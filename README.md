# Bardi Wi-Fi switch controller

An experimental cloud-free LAN controller and LLM adaptation guide for a tested
Bardi smart-switch profile using Tuya protocol 3.4.

The controller provides fresh status, explicit On and Off, electrical telemetry,
and an Off/On demonstration that restores power and checks unchanged settings.
It uses TinyTuya rather than implementing another Tuya transport. It runs on
macOS or Linux with Python 3.11 or later. Windows is not supported because the
state lock uses `fcntl`.

## What cloud-free means here

Commands go directly to the switch's LAN address on TCP port 6668. The runtime
does not use Bardi, an emulator, a Tuya account, or cloud APIs.

You must already have the switch's device ID and 16-byte local key. The tested
key came from an owner-authorized, offline inspection of the already-paired
app's cache. This does **not** provide cloud-free initial enrollment from a
factory-fresh switch. The bulb's BLE setup command is not a Wi-Fi switch setup
command. See [the research method](RESEARCH.md).

The switch may still maintain its own vendor-cloud connection. This project
does not change router rules or claim that the switch itself is internet-isolated.

## Set up local control

Clone the repository and install the dependency in a virtual environment:

```sh
git clone https://github.com/samueljseay/bardi-wifi-switch-controller.git
cd bardi-wifi-switch-controller
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
install -d -m 700 "$HOME/.local/state/bardi-switch"
```

Create `target.json` inside that private state directory with your own values.
Use a local editor, not command-line arguments or chat, to enter the key.
The following is a template, not a working device record:

```json
{
  "device_id": "YOUR_DEVICE_ID",
  "address": "YOUR_PRIVATE_LAN_IP",
  "local_key": "YOUR_16_BYTE_LOCAL_KEY",
  "version": "3.4"
}
```

Set the file mode to 0600:

```sh
chmod 600 "$HOME/.local/state/bardi-switch/target.json"
```

Confirm that discovery, the app's device information, and your credential source
identify the same device. A broadcast announcement alone is not authentication.
Verify the current LAN address after DHCP changes. Never guess keys, send raw
datapoints, or copy another device's credentials.

Start with a read-only query:

```sh
.venv/bin/python switch.py --state "$HOME/.local/state/bardi-switch" status
```

Output includes `power_on`, `watts`, `volts`, `milliamps`, countdown seconds,
and fault bits. Measurements are device reports, not independently calibrated
measurements. A fresh response can contain older meter samples.

After verifying the device and a safe load, use explicit power commands:

```sh
.venv/bin/python switch.py --state "$HOME/.local/state/bardi-switch" off
.venv/bin/python switch.py --state "$HOME/.local/state/bardi-switch" on
```

An already-correct relay state is a no-op. The controller refuses changes if
countdown, fault, or automation fields are active or unknown. This conservative
profile expects the tested schema and is not a universal Tuya switch driver.

## Run the demonstration

Use `demo` only with a light or another load that can safely lose power.
Do not use it on a compressor, refrigerator, heater, computer, medical device,
or another load that needs a specific shutdown or restart procedure.

```sh
.venv/bin/python switch.py --state "$HOME/.local/state/bardi-switch" demo
```

The supply must start On. The demo switches it Off, confirms fresh Off status,
waits five seconds, queries it again, and restores On. It compares the final
startup, indicator, lock, protection, and automation settings with the baseline.
These settings are observed, not rewritten. A physical supply interruption can
also reboot the attached bulb. The program does not reconfigure that bulb.

The demo attempts a bounded On restoration after an error or keyboard interrupt
when fresh observations permit it. Network loss, process termination, or loss of
host power can still leave the supply Off. Arrange physical recovery first.

## Handle uncertainty without repeating a write

The controller records a durable intent before each relay command. It uses an
authenticated connection with retransmission disabled for that command. A new
connection must then report the requested state before the command is complete.
It does not treat a transport send or an empty acknowledgment as confirmation.

An interrupted or uncertain operation leaves `pending-write.json`. It blocks
later power commands across process restarts. Status remains available:

```sh
.venv/bin/python switch.py --state "$HOME/.local/state/bardi-switch" status
.venv/bin/python switch.py --state "$HOME/.local/state/bardi-switch" reconcile
```

`reconcile` only reads the switch. It resolves the pending operation if the
requested state is now observed. It does not resend the command. If the state
does not match, stop and inspect the retained intent and recovery options.
Never delete the pending file just to make another command run.

Keep one state directory per switch. Do not use the vendor app, another local
controller, or physical controls concurrently with a demonstration.

## Test and adapt

```sh
.venv/bin/python -B -I -m unittest discover -s . -v
```

The tests use synthetic identities, a simulated device, and the installed
TinyTuya packet parser. They disable network sockets and do not require a switch.
Read [AGENTS.md](AGENTS.md) before asking an LLM to adapt the controller.
See [EVIDENCE.md](EVIDENCE.md) for tested behavior and limits.

Keep private state outside the source tree. Never publish device IDs, keys,
addresses, raw captures, app data, emulator images, or debug logs. Do not enable
TinyTuya debug logging with real credentials.

## Related project and license

For bulb control over Bluetooth, see
[Bardi BLE controller](https://github.com/samueljseay/bardi-ble-controller).
Its BLE setup and lighting commands are separate from this switch's LAN control.

Project code, tests, and documentation are licensed under [Apache-2.0](LICENSE).
See [NOTICES.md](NOTICES.md) for dependency attribution and distribution limits.
