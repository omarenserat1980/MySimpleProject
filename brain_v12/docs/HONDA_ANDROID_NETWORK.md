# Brain Honda Android Network Project

## Primary objective

Enable a reliable, repeatable way to provide Android app connectivity and supported app projection on the user's China-market Honda e:NP1 head unit, using a Realme RMX3710 phone. Honda CONNECT activation is a separate diagnostic track; it is not a prerequisite for Android phone internet sharing unless the head unit's actual hardware/software contract proves otherwise.

## Brain-owned SQLite memory

Brain stores the project memory locally at:

`~/.electronic_brain/state/honda_android_network.sqlite3`

Override with `BRAIN_HONDA_NETWORK_DB`, or use `BRAIN_STATE_DIR` to change the Brain state directory. The VIN is deliberately not committed to the repository. To store it locally, set `BRAIN_VEHICLE_VIN` when initializing. Do not print or commit the VIN.

Initialize and inspect:

```bash
python -m brain_v12.vehicle_network.memory init
python -m brain_v12.vehicle_network.memory status
```

This uses Python's standard-library sqlite3 module; no paid service or external database is required.

## Current baseline (conversation-derived; not all independently verified)

- Vehicle: Honda e:NP1, model year 2023 (reported by user).
- Purchased new in Jordan.
- VIN was supplied by the user, but is intentionally not embedded in source control.
- Head-unit software version: 01.000.400.
- Honda CONNECT 3.0 identity verification screen appears but does not display the QR code.
- Visible menus previously inspected did not show WLAN/Network settings.
- Phone: Realme RMX3710 / C66, Android 15.
- Baidu CarLife EX phone app version: 8.9.5.
- Phone was connected to the head unit's DATA USB port; USB media screen recognized the phone.
- USB tethering was not established. Phone USB state remained `accessory,adb`; RNDIS did not persist.
- CarLife Super Cast unlock command reported success, but YouTube projection remained white. This is not a successful projection result.

## Evidence versus hypotheses

The manufacturer identity (GAC Honda vs Dongfeng Honda), exact head-unit manufacturer/model, TCU model, USB RNDIS host support, and current server provisioning status are not yet independently verified. Do not assume that an ENS1/Dongfeng manual or M-NV manual exactly describes this e:NP1 configuration.

## Investigation plan

1. **Identify the head unit**: collect full About/version information including system version, software version, hardware version, MCU, VIN display, ICCID/PDSN if present. Redact ICCID and never expose the full VIN in logs.
2. **Identify supported network interfaces**: determine from the exact head-unit hardware/manual whether USB RNDIS, USB ECM/NCM, Wi-Fi client, Bluetooth PAN, or phone projection networking is supported. A USB data port or USB media playback does not prove RNDIS host support.
3. **Validate the phone-side path**: test Android USB tethering only through normal user-facing settings and verify the phone reports an active tethering interface. Do not force hidden system properties or privileged USB functions.
4. **Validate head-unit path**: test only a documented supported interface. Record interface state and evidence. No factory reset, generic firmware, rooting, or unsigned APK sideloading as a first-line fix.
5. **Android apps**: distinguish native installation on the head unit from phone projection. Test a single harmless app first. YouTube white-screen behavior must be treated as an unresolved receiver compatibility issue.
6. **Honda CONNECT**: separately request the correct Honda entity to verify VIN registration, TCU provisioning, SIM/ICCID status, and QR generation. Do not infer a TCU hardware failure from a missing QR alone.

## Acceptance criteria

The goal is complete only when:
- a network path from the phone to the head unit is verified with observable connectivity evidence; and
- the intended Android apps are usable through a documented compatible installation or projection method; and
- results are classified as `REAL_PASS` only with target-specific evidence. A plan, simulator result, unlock message, or USB media detection is not proof.

## Safety and privacy

- VIN and ICCID are private vehicle identifiers. Keep them in local Brain state only.
- Never commit VIN, ICCID, credentials, account tokens, or personal identity documents.
- Never run factory reset, firmware flashing, root commands, or hidden USB mode overrides without exact model compatibility, recovery procedure, and explicit approval.
