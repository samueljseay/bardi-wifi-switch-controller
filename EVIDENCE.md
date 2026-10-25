# Verification and limits

The tested device is a Bardi mains switch powering a Bardi light bulb.
Its app displayed Main Module 1.1.17 and Other type 1.0.7. Authenticated LAN
control used Tuya protocol 3.4. These version strings do not identify its chip
or establish compatibility with another firmware or a CloudCutter profile.

## Verified on the owner's switch

- Recovered the exact saved switch's cached local key without a cloud request.
  An offline disposable emulator copy supplied the cache. The original
  installed app and its userdata were retained.
- Authenticated directly over LAN and read all reported datapoints.
- Ran the standalone CLI with its process restricted to the target's TCP port
  6668. Other connections, UDP transmissions, and external DNS were forbidden.
- Switched the relay Off, confirmed it on a separate connection, held Off for
  five seconds, and read Off again. The switch's meter then reported zero load.
- Restored On and confirmed that startup, protection, indicator, child-lock,
  countdown, and schedule settings matched the initial observations.
- The attached bulb subsequently answered a separate direct BLE handshake and
  state query. It reported On and its previous white-light settings.
- No uncertain relay intent remained after the demonstration.

The control run did not invoke an emulator or app and made no cloud connection.
The installed switch's own internet access was not blocked or measured.

## Offline checks

Twelve synthetic tests cover explicit states and no-ops, metric scaling, Boolean
validation, active automation refusal, uncertainty across restarts, read-only
reconciliation, demo restoration, keyboard interruption, process locking, and
private credential modes. They also verify recovery after interrupted journal
publication and rejection of a corrupted status HMAC through the real packet
parser. No test connects to a device.

TinyTuya 1.20.0's 3.4 receive path exposes HMAC validation as `crc_good` but does
not reject failed HMACs. This controller explicitly rejects those frames before
decoding them. A fresh read using that enforcement succeeded on the switch.

A separate socket-disabled experiment against the pinned TinyTuya library
exercised a send that times out after transmission. With an existing session and
retry limit zero, exactly one synthetic packet was sent and no reconnect was
attempted. Another experiment accepted a correct synthetic 3.4 challenge and
rejected wrong-key and wrong-HMAC responses.

## Not established

- Cloud-free initial enrollment of a factory-fresh switch. The tested key
  originated from an already-paired app's local cache.
- Compatibility with other switch models or firmware.
- Operation after the switch's own incoming mains supply is removed and restored.
  Switching its output relay does not reboot its Wi-Fi processor.
- Independent optical or calibrated electrical confirmation of the demo.
  Relay and meter values are reports from the device. Meter samples lagged
  the immediate relay changes, including a zero reading shortly after On.
- Safe operation of timers, startup preferences, protection, lock, indicator,
  or schedule writes. The controller leaves these unchanged.

Private evidence and credentials are deliberately not bundled with this source.
The repository contains the controller, synthetic tests, and research guidance,
not raw captures, emulator data, or device-specific credentials.
