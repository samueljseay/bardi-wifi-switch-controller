"""Local Tuya 3.4 relay control. No app, cloud API, or key-discovery operation."""
import argparse
from contextlib import contextmanager
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import uuid


class ControlError(Exception):
    pass


def private(path, directory=False):
    info = path.lstat()
    correct_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not correct_type or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600):
        raise ControlError('State must use owned directories with mode 0700 and files with mode 0600')


def load(path):
    private(path)
    with path.open() as handle:
        return json.load(handle)


def save(path, value):
    private(path.parent, directory=True)
    fd, temporary = tempfile.mkstemp(prefix='.journal-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        # Publish complete JSON without replacing an existing journal entry.
        os.link(temporary, path)
        sync(path.parent)
    finally:
        os.unlink(temporary)


def sync(directory):
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def snapshot(response):
    dps = response.get('dps') if isinstance(response, dict) else None
    if not isinstance(dps, dict) or type(dps.get('1')) is not bool:
        raise ControlError('No valid fresh relay status received')
    return dps


def summary(dps):
    return {'power_on': dps['1'], 'countdown_seconds': dps.get('9'),
            'watts': dps['19'] / 10 if type(dps.get('19')) is int else None,
            'volts': dps['20'] / 10 if type(dps.get('20')) is int else None,
            'milliamps': dps.get('18'), 'fault_bits': dps.get('26')}


def safe_to_switch(dps):
    if type(dps.get('9')) is not int or dps['9'] != 0:
        raise ControlError('Refusing to disturb an active or unknown countdown')
    if any(dps.get(key) != '' for key in ('42', '43', '44')):
        raise ControlError('Refusing to disturb active or unknown automation')
    if type(dps.get('26')) is not int or dps['26'] != 0:
        raise ControlError('Refusing power changes while faults are reported or unknown')


class Controller:
    def __init__(self, state):
        self.state = Path(state).absolute()
        private(self.state, directory=True)
        self.target = load(self.state / 'target.json')
        target = self.target
        if target.get('version') != '3.4' or not isinstance(target.get('device_id'), str) or not target['device_id']:
            raise ControlError('A device ID and verified LAN version 3.4 are required')
        if not isinstance(target.get('local_key'), str) or len(target['local_key'].encode('latin1')) != 16:
            raise ControlError('A 16-byte local key is required')
        if not ipaddress.ip_address(target['address']).is_private:
            raise ControlError('Only a private LAN address is accepted')
        self.pending = self.state / 'pending-write.json'

    @contextmanager
    def locked(self):
        fd = os.open(self.state / 'controller.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ControlError('Another controller owns this state directory') from None
            yield self
        finally:
            os.close(fd)

    def device(self):
        import tinytuya

        class AuthenticatedOutlet(tinytuya.OutletDevice):
            def _receive(self):
                message = super()._receive()
                # TinyTuya 1.20.0 checks GCM tags but not 3.4/55AA HMACs here.
                if not message.crc_good:
                    raise ControlError('Response authentication failed')
                return message

        target = self.target
        device = AuthenticatedOutlet(target['device_id'], target['address'], target['local_key'],
                                     version=3.4, connection_timeout=3, connection_retry_limit=1,
                                     connection_retry_delay=0, persist=True)
        device.set_retry(False)
        return device

    def status(self):
        device = self.device()
        try:
            return snapshot(device.status())
        finally:
            device.close()

    def finish(self, intent, observed, reconciled=False):
        save(self.state / (intent['operation_id'] + '-result.json'),
             {'confirmed_by_fresh_status': True, 'reconciled': reconciled,
              'datapoints': observed, 'completed_epoch': time.time()})
        self.pending.unlink()
        sync(self.state)

    def reconcile(self):
        observed = self.status()
        if not self.pending.exists():
            return {'pending': False, 'status': summary(observed)}
        intent = load(self.pending)
        if observed['1'] is not intent['desired_on']:
            raise ControlError('Pending write still unresolved; no command was repeated')
        result = self.state / (intent['operation_id'] + '-result.json')
        if result.exists():
            load(result)
            self.pending.unlink()
            sync(self.state)
        else:
            self.finish(intent, observed, reconciled=True)
        return {'pending': False, 'reconciled': True, 'status': summary(observed)}

    def power(self, desired):
        if type(desired) is not bool:
            raise ControlError('Power must be a Boolean, never a toggle')
        if self.pending.exists():
            raise ControlError('An uncertain write exists; use read-only reconcile first')
        device = self.device()
        try:
            before = snapshot(device.status())
            if before['1'] is desired:
                return {'changed': False, 'status': summary(before)}
            safe_to_switch(before)
            intent = {'operation_id': str(uuid.uuid4()), 'desired_on': desired,
                      'before': before, 'started_epoch': time.time()}
            save(self.state / (intent['operation_id'] + '-intent.json'), intent)
            save(self.pending, intent)
            # Authenticate first, then forbid reconnects and retransmission for the write.
            device.set_socketRetryLimit(0)
            response = device.set_status(desired, switch=1, nowait=True)
            if response is not None:
                raise ControlError('Write outcome uncertain; use read-only reconcile')
        finally:
            device.close()
        for _ in range(3):
            time.sleep(0.25)
            observed = self.status()
            if observed['1'] is desired:
                self.finish(intent, observed)
                return {'changed': True, 'status': summary(observed)}
        raise ControlError('Desired state was not confirmed; write remains pending')

    def demo(self, off_seconds=5):
        if not 1 <= off_seconds <= 10:
            raise ControlError('Demo Off interval must be between 1 and 10 seconds')
        before = self.status()
        safe_to_switch(before)
        if before['1'] is not True:
            raise ControlError('Demo requires an initially On supply')
        operation = str(uuid.uuid4())
        save(self.state / (operation + '-demo-intent.json'), {'before': before, 'off_seconds': off_seconds})
        try:
            off = self.power(False)
            time.sleep(off_seconds)
            off_held = self.status()
            if off_held['1'] is not False:
                raise ControlError('Relay did not remain Off during demonstration')
            on = self.power(True)
            time.sleep(2)
            after = self.status()
            settings = ('9', '38', '39', '40', '41', '42', '43', '44')
            restored = after['1'] is True and all(key in before and key in after and after[key] == before[key]
                                                 for key in settings)
            if not restored:
                raise ControlError('Complete settings restoration was not confirmed')
            result = {'off': off, 'off_held': summary(off_held), 'on': on, 'final': summary(after),
                      'settings_restored': True, 'cloud_requests': 0,
                      'optical_output_verified': False}
            save(self.state / (operation + '-demo-result.json'), result)
            return result
        except BaseException:
            # Restore only after a fresh observation can resolve any uncertain write.
            if self.pending.exists():
                self.reconcile()
            self.power(True)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True, help='Private directory containing target.json')
    parser.add_argument('command', choices=('status', 'on', 'off', 'demo', 'reconcile'))
    args = parser.parse_args()
    try:
        with Controller(args.state).locked() as control:
            if args.command == 'status':
                result = summary(control.status())
            elif args.command == 'reconcile':
                result = control.reconcile()
            elif args.command == 'demo':
                result = control.demo()
            else:
                result = control.power(args.command == 'on')
        print(json.dumps(result, sort_keys=True))
    except ControlError as error:
        print(json.dumps({'error': str(error)}))
        return 1
    except Exception:
        print(json.dumps({'error': 'Operation failed. Inspect private state and use status or reconcile before another write.'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
