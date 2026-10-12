# Electronic Brain — Virtual Hardware Device Catalog

This is the common index of electronic device families and typical hardware-component classes for Electronic Brain. It is designed as a starting point for adding specific, tested virtual device profiles.

## Family coverage

Desktop PCs; laptops and notebooks; servers/workstations; phones and tablets; PlayStation/Xbox/Nintendo and handheld gaming; networking and telecom appliances; compute/board components; storage systems; displays and projectors; audio/video/cameras/streaming; wearables and AR/VR; smart-home appliances; office/printer devices; vehicle and transport electronics; medical equipment; scientific instruments; robotics/industrial control; power/energy electronics; peripherals/accessories; satellite/space systems; embedded/IoT modules.

The component-class index covers CPU/SoC, GPU/NPU/DSP/FPGA/microcontrollers, RAM/ECC/cache, firmware, storage and controllers, motherboard/chipset, PCIe/USB/I2C/SPI/GPIO, network adapters/radios, display/camera/audio/input, sensors, battery/PMIC/PSU, cooling, security, clocks/watchdogs, actuators, and specialist I/O.

## Python API

```python
from brain_v12.virtual_hardware.device_catalog import (
    get_device_family, list_device_families, list_component_classes, validate_catalog
)
families = list_device_families()
laptop = get_device_family("laptop")
components = list_component_classes()
assert validate_catalog()["ok"]
```

- `list_device_families(category=None)`: stable inventory, optionally filtered.
- `get_device_family(family_id)`: family plus resolved component inventory and limitations.
- `list_component_classes()`: canonical hardware-component classes.
- `validate_catalog()`: checks component references and catalog invariants.

## Accuracy contract

Every catalog entry is explicitly marked `CATALOGED_NOT_FULLY_EMULATED`. Cataloging a device family does not claim that a specific retail model, proprietary firmware, full protocol stack, or original operating system is emulated. Exact bill of materials and specifications vary by model/SKU; source-backed profiles and conformance tests must be added before stronger status labels are justified.

All models are software-only by default. The catalog does not open host hardware or create physical compute capacity. It does not perform RF transmission, medical treatment, vehicle actuation, or external real-world I/O. Power, thermal, sensor and performance values remain estimates unless documented and calibrated.

Recommended implementation stages: source-backed model profiles; device-specific register/bus/protocol behavior; firmware and guest OS compatibility tests; reproducible conformance suites; explicit feature status (cataloged, implemented, tested, guest-compatible, hardware-calibrated).
