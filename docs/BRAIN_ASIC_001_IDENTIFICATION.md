# BRAIN-ASIC-001 identification and discovery

## Canonical identity

- Brain asset label: `BRAIN-ASIC-001`
- Compute-device reference: `BRAIN-ASIC-001-U1`
- Board reference: `BRAIN-ASIC-001-PCB1`

These are internal Brain identifiers. They are **not** a manufacturer model, chip serial number, proof of fabrication, or proof that a board is connected.

## Information needed to identify the real device

Record only values visible on the actual hardware, vendor documentation, or read-only operating-system discovery:

1. Manufacturer and exact board/model name.
2. Exact ASIC chip part number, from a legible chip marking or authoritative bill of materials/datasheet. Do not assume BM1362 or any other model.
3. Manufacturer serial number and lot/batch, if present.
4. USB VID/PID and USB serial, or the actual transport and device path (USB, UART, Ethernet, etc.).
5. Host address/port only if the board genuinely exposes a documented network interface. Never guess a host or port.
6. Official datasheet/product URL and evidence such as a label/photo, device enumeration output, and connection-test log.

Do not publish credentials, pool passwords, access tokens, private keys, or other secrets in the registry.

## Create a record

Prepare a local JSON file with known facts only; unknown fields may be omitted:

```json
{
  "manufacturer": "value read from device/vendor",
  "device_model": "exact model",
  "chip_part_number": "exact marked part number",
  "board_model": "exact board model",
  "manufacturer_serial_number": "serial read from label/device",
  "transport": "usb",
  "usb_vid": "1d6b",
  "usb_pid": "0002",
  "usb_serial": "serial reported by OS",
  "datasheet_url": "https://vendor.example/datasheet",
  "discovery_method": "read_only_os_enumeration"
}
```

The example VID/PID values are syntax examples only, not ASIC-001 identifiers. Replace them with the actual observed values. Do not set verification flags unless the corresponding evidence exists.

Run:

```bash
python -m brain_v12.asic.unit_001.identity_registry --input /path/to/asic-001-identity.json --stdout
```

The validator writes a normalized identity record. It keeps unknowns null and uses separate gates for identity completeness, physical-hardware verification, and live-mining evidence. A live-mining status requires independent evidence of physical identity, a tested connection, and an accepted pool share.

## Current blocker

Until an actual device is physically observed and its identifying evidence is recorded, status must remain `IDENTIFICATION_INCOMPLETE`. A passing simulator or RTL test does not identify physical hardware and does not prove mining.
