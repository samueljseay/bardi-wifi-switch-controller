# Guidance for agents adapting this controller

Use this project as a starting point for an owner's device, not proof that every
Bardi switch has the tested schema. Read README.md and EVIDENCE.md first.

## Establish the target before a write

- Obtain explicit authority for the device and connected load.
- Establish the exact device ID, LAN protocol, address, and existing local key.
  Do not transmit them to a public service or include them in a repository.
- Start with authenticated read-only status. Match its datapoints to the actual
  product schema. Do not infer meanings solely from familiar DP numbers.
- Keep existing factory keys, raw app data, account tokens, and unrelated device
  records out of stdout, chat, source, and fixtures.
- Do not reset, re-pair, flash, or replace keys merely because authentication
  fails. A reset can invalidate the existing key and remove the recovery path.

## Preserve the tested control contract

DP1 is a Boolean relay on the tested switch. DP9 is countdown seconds. DP18 is
milliamps. DP19 and DP20 have scale 1 for watts and volts. These facts come from
this device's cached schema and authenticated reports, not all Tuya products.

The current driver only writes DP1. Keep persistent startup preferences,
overcharge protection, child lock, indicator settings, and encoded schedules
read-only unless separately requested and understood. Never brute-force DPs.

Use explicit desired states, not toggle commands. Authenticate before sending.
Preserve the no-retransmission write path, durable pending state, process lock,
and fresh-connection confirmation. A cached value or send success is not proof
of a new state. Use the CLI so ownership is locked for the entire operation.

Do not delete pending intents or silently change protocols or key sources after
an error. Reconcile through a fresh read. Keep physical recovery available.

## Prove the result

Run the synthetic tests before live work. Test error paths with a simulator,
not repeated physical switching. With authorization and a safe load, demonstrate
one bounded Off/On sequence, check fresh status, and restore the baseline.

Keep distinct claims for authenticated reports, meter readings, human observation,
and independent physical measurements. A fresh status response does not imply
its electrical samples were measured at that exact moment.

The runtime must remain independent of app extraction and research equipment.
Existing-key local control is not cloud-free factory enrollment. Do not claim
the switch has been cut off from its cloud without separate network evidence.
