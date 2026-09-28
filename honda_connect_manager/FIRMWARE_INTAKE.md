# Honda CONNECT 3.0 firmware intake

Place the vehicle-generated export file on a local machine/USB copy. The Brain
accepts a JSON export such as:

- `HondaSoftwareUpdates/rb/update_by_usb.json`
- `update_by_usb.json`

Run:

```bash
python honda_connect_manager/brain.py --vehicle-json /path/to/update_by_usb.json
```

The Brain extracts system/software/hardware/MCU versions, firmware/package
metadata and then applies only explicit compatibility rules from `apps.json`.

Important: finding a package filename or URL does **not** authorize installation.
The package must be verified for the exact head unit and installed only through
Honda's supported mechanism. The Brain deliberately keeps
`automatic_install_allowed` false.
