# How the existing local key was recovered

This is a record of the method used on an owner's already-paired switch.
It is not a universal setup script or permission to inspect someone else's app.
Do not use cloud key APIs or upload app data to an LLM or public service.

## The useful distinction

The tested bulb accepted a local BLE setup operation. The Wi-Fi switch instead
required its existing per-device LAN key for the Tuya 3.4 authenticated session.
Publicly decodable discovery broadcasts did not contain that key.

Tuya's AP and Bluetooth activation "without internet" documentation still has
the app obtain activation information from the cloud. It does not establish a
cloud-free key-installation path for this switch. No reset was needed once an
existing cached key became available.

## The local-cache method

The existing dedicated Android emulator used a Google Play production image.
Its shell could not read the non-debuggable app's private storage. Shared
preferences did not expose the switch key in plain text. Device caches used
encrypted MMKV storage.

The investigation used these steps:

1. Verify the dedicated emulator and exact saved device identity.
2. Force-stop Bardi. Disable the emulator's Wi-Fi and cellular networking.
   Retain the original network settings for restoration.
3. Stop that emulator cleanly and make a private, consistent rollback copy.
   Never wipe the original or change its Google Play system image.
4. Prepare a disposable copy using an installed Android debug image at the same
   API level and architecture. Preserve both userdata and encryption metadata.
5. Flatten the copied qcow2 overlay chains before passing explicit data and
   encryption images to the inspection emulator. Copying only a base image
   loses the actual app data. Never experiment against the original images.
6. Verify that the disposable copy contains the app data, has no default network
   route, and has its guest radios disabled before opening Bardi.
7. Use a matching Frida server and host binding on that disposable copy. Invoke
   only the cached DeviceBean getter for the exact expected device ID. Read its
   device ID, local key, and product schema. Do not enumerate or retain other
   devices, login tokens, Google account material, or broad app logs.
8. Require an exact device-ID match and a 16-byte key. Save only the needed
   switch record in a mode-0600 file inside a mode-0700 private directory.
9. Shut down the inspection copy. Restore the original emulator's normal boot
   and network settings. Remove disposable copies and instrumentation binaries.
10. Verify a fresh matching LAN announcement, then use the recovered key for
    authenticated read-only status before attempting any relay write.

The inspected SDK exposes
`com.thingclips.sdk.ble.core.business.ModuleBusiness.INSTANCE.getDeviceBean(id)`.
Its DeviceBean has `getDevId()`, `getLocalKey()`, `getDps()`, and `getSchema()`.
These are version-specific implementation details, not stable public recovery
APIs. Frida 17.24.3 with its Java bridge was used for the final extraction.

Do not confuse DeviceBean's `getPv()` with the LAN discovery version. Here it
returned 2.2 while authenticated LAN control used 3.4. App product ID and the
discovery product key were also different fields. The cached IP was not the
current LAN address. Fresh discovery and authentication resolved those gaps.

## Privacy and recovery

An emulator data image can contain credentials for every signed-in account.
Keep rollback copies private, local, and outside repositories. Do not publish
or transfer them as troubleshooting artifacts. Remove disposable copies when
the original emulator and extracted switch record have been verified.

A recovered key can become invalid after re-pairing or a factory reset. Preserve
the working setup and a physical recovery method. This method provides existing-
key local control, not independent activation of an unpaired device.
