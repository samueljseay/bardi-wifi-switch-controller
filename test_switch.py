import copy
import json
from pathlib import Path
import socket
import tempfile
import types
import unittest
from unittest.mock import patch

from switch import Controller, ControlError, save, summary


class SwitchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name)
        self.state.chmod(0o700)
        save(self.state / 'target.json', {'device_id': 'synthetic-switch',
             'address': '192.168.123.234', 'local_key': '0123456789abcdef', 'version': '3.4'})
        self.dps = {'1': True, '9': 0, '18': 73, '19': 173, '20': 2387, '26': 0,
                    '38': 'memory', '39': False, '40': 'relay', '41': False,
                    '42': '', '43': '', '44': ''}
        self.transitions = []
        self.write_mode = 'normal'
        case = self

        class Device:
            def __init__(self, *args, **kwargs):
                self.authenticated = False
                self.limit = kwargs['connection_retry_limit']

            def set_retry(self, enabled):
                pass

            def set_socketRetryLimit(self, limit):
                self.limit = limit

            def status(self):
                self.authenticated = True
                return {'dps': copy.deepcopy(case.dps)}

            def set_status(self, desired, switch, nowait):
                if not self.authenticated or self.limit != 0 or switch != 1 or nowait is not True:
                    raise AssertionError('Write must use an authenticated session without retries')
                if case.write_mode == 'ignored':
                    return None
                case.dps['1'] = desired
                case.transitions.append(desired)
                if case.write_mode == 'lost_reply':
                    raise OSError('Synthetic lost response after applying command')
                return None

            def close(self):
                pass

        self.module = patch.dict('sys.modules', {'tinytuya': types.SimpleNamespace(OutletDevice=Device)})
        self.module.start()
        self.addCleanup(self.module.stop)
        self.sleep = patch('switch.time.sleep')
        self.sleep.start()
        self.addCleanup(self.sleep.stop)
        self.network = patch.object(socket, 'socket', side_effect=AssertionError('Network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.control = Controller(self.state)

    def test_status_and_units(self):
        with self.control.locked():
            result = summary(self.control.status())
        self.assertEqual(result, {'power_on': True, 'countdown_seconds': 0,
                         'watts': 17.3, 'volts': 238.7, 'milliamps': 73, 'fault_bits': 0})
        self.assertEqual(self.transitions, [])

    def test_explicit_off_then_on_and_noop(self):
        with self.control.locked():
            off = self.control.power(False)
            on = self.control.power(True)
            again = self.control.power(True)
        self.assertEqual([off['status']['power_on'], on['status']['power_on']], [False, True])
        self.assertEqual(self.transitions, [False, True])
        self.assertEqual(again, {'changed': False, 'status': summary(self.dps)})
        self.assertFalse((self.state / 'pending-write.json').exists())

    def test_boolean_relay_is_required(self):
        self.dps['1'] = 1
        with self.assertRaises(ControlError):
            self.control.status()
        self.dps['1'] = False
        self.assertEqual(self.control.status()['1'], False)

    def test_active_or_unknown_automation_blocks_changes(self):
        for key, bad in [('9', 15), ('9', False), ('42', 'schedule'), ('43', None), ('26', 2)]:
            with self.subTest(key=key, value=bad):
                original = self.dps[key]
                self.dps[key] = bad
                with self.assertRaises(ControlError):
                    self.control.power(False)
                self.assertIs(self.control.status()['1'], True)
                self.dps[key] = original
        self.assertEqual(self.control.power(False)['status']['power_on'], False)
        self.assertEqual(self.transitions, [False])

    def test_uncertain_write_survives_restart_and_reconciles_without_repeating(self):
        self.write_mode = 'lost_reply'
        with self.assertRaises(OSError):
            self.control.power(False)
        replacement = Controller(self.state)
        with self.assertRaises(ControlError):
            replacement.power(True)
        result = replacement.reconcile()
        self.assertEqual(result['status']['power_on'], False)
        self.assertEqual(result['reconciled'], True)
        self.assertEqual(self.transitions, [False])
        self.write_mode = 'normal'
        self.assertEqual(replacement.power(True)['status']['power_on'], True)
        self.assertEqual(self.transitions, [False, True])

    def test_unapplied_write_remains_blocked(self):
        self.write_mode = 'ignored'
        with self.assertRaises(ControlError):
            self.control.power(False)
        with self.assertRaises(ControlError):
            Controller(self.state).reconcile()
        with self.assertRaises(ControlError):
            Controller(self.state).power(True)
        self.assertIs(self.control.status()['1'], True)
        self.assertEqual(json.loads((self.state / 'pending-write.json').read_text())['desired_on'], False)

    def test_demo_restores_power_and_settings(self):
        before = copy.deepcopy(self.dps)
        result = self.control.demo()
        self.assertEqual(result['off']['status']['power_on'], False)
        self.assertEqual(result['on']['status']['power_on'], True)
        self.assertEqual(result['settings_restored'], True)
        self.assertEqual(self.dps, before)
        self.assertEqual(self.transitions, [False, True])

    def test_interrupted_demo_restores_on(self):
        def interrupted(seconds):
            if seconds == 5:
                raise KeyboardInterrupt
        with patch('switch.time.sleep', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.control.demo()
        self.assertEqual(self.transitions, [False, True])
        self.assertIs(self.control.status()['1'], True)

    def test_interrupted_result_publication_can_reconcile_and_restore(self):
        original_dump = json.dump
        interrupted = False

        def interrupted_dump(value, handle, **kwargs):
            nonlocal interrupted
            if value.get('confirmed_by_fresh_status') and not interrupted:
                interrupted = True
                handle.write('{')
                raise OSError('Synthetic interruption while saving confirmation')
            return original_dump(value, handle, **kwargs)

        with patch('switch.json.dump', side_effect=interrupted_dump):
            with self.assertRaises(OSError):
                self.control.power(False)
        restarted = Controller(self.state)
        self.assertEqual(restarted.reconcile()['status']['power_on'], False)
        self.assertEqual(self.transitions, [False])
        self.assertEqual(restarted.power(True)['status']['power_on'], True)
        self.assertEqual(self.transitions, [False, True])
        self.assertFalse(self.control.pending.exists())
        self.assertEqual(list(self.state.glob('.journal-*')), [])

    def test_second_process_cannot_own_state(self):
        with self.control.locked():
            with self.assertRaises(ControlError):
                with Controller(self.state).locked():
                    pass
            self.assertIs(self.control.status()['1'], True)

    def test_world_readable_credentials_are_rejected(self):
        (self.state / 'target.json').chmod(0o644)
        with self.assertRaises(ControlError):
            Controller(self.state)
        (self.state / 'target.json').chmod(0o600)
        self.assertIs(Controller(self.state).status()['1'], True)


class AuthenticationTests(unittest.TestCase):
    def test_status_rejects_corrupted_hmac_with_real_transport_parser(self):
        from tinytuya.core.crypto_helper import AESCipher
        from tinytuya.core.message_helper import TuyaMessage, pack_message

        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            state.chmod(0o700)
            save(state / 'target.json', {'device_id': 'synthetic-switch',
                 'address': '192.168.123.234', 'local_key': '0123456789abcdef', 'version': '3.4'})
            control = Controller(state)
            key = b'0123456789abcdef'
            encrypted = AESCipher(key).encrypt(b'{"dps":{"1":true}}', use_base64=False)
            packet = pack_message(TuyaMessage(1, 8, 0, b'\x00' * 4 + encrypted, 0), hmac_key=key)

            class Stream:
                def __init__(self, data):
                    self.data = data

                def recv(self, length):
                    result, self.data = self.data[:length], self.data[length:]
                    return result

                def close(self):
                    pass

            with patch.object(socket, 'socket', side_effect=AssertionError('Network forbidden')):
                for corrupted in (False, True):
                    with self.subTest(corrupted=corrupted):
                        data = bytearray(packet)
                        if corrupted:
                            data[-5] ^= 1
                        device = control.device()
                        device.socket = Stream(bytes(data))
                        try:
                            if corrupted:
                                with self.assertRaises(ControlError):
                                    device._receive()
                            else:
                                message = device._receive()
                                self.assertEqual(device._decode_payload(message.payload), {'dps': {'1': True}})
                        finally:
                            device.close()


if __name__ == '__main__':
    unittest.main()
