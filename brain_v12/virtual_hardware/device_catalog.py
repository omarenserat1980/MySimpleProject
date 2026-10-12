"""Extensible software-only catalog of electronic device families and their hardware classes.

Catalog presence is not evidence of complete device emulation. Exact component selection
and commercial model specifications must be supplied by source-backed device profiles.
"""
from __future__ import annotations
from copy import deepcopy

COMPONENT_CLASSES = {
 "cpu": ("CPU / SoC", "compute", "ISA_or_functional_model"),
 "gpu": ("GPU / graphics accelerator", "compute", "functional_or_statistical"),
 "npu": ("NPU / AI accelerator", "compute", "workload_estimation"),
 "dsp": ("Digital signal processor", "compute", "functional_model"),
 "fpga": ("FPGA / programmable logic", "compute", "configuration_dependent"),
 "microcontroller": ("Microcontroller", "compute", "firmware_dependent"),
 "ram": ("RAM / ECC RAM", "memory", "functional_memory"),
 "cache": ("L1/L2/L3 cache", "memory", "timing_model"),
 "rom_firmware": ("ROM / BIOS / UEFI / device firmware", "firmware", "firmware_dependent"),
 "storage": ("SSD / HDD / flash / eMMC / UFS", "storage", "block_or_metadata_model"),
 "storage_controller": ("SATA / NVMe / SCSI / eMMC controller", "storage", "protocol_dependent"),
 "motherboard": ("Motherboard / system board", "platform", "topology_model"),
 "chipset": ("Chipset / SoC interconnect", "platform", "topology_model"),
 "pcie": ("PCIe / PCI / CXL fabric", "interconnect", "transaction_level"),
 "usb": ("USB controller and ports", "interconnect", "class_and_state_model"),
 "i2c_spi_gpio": ("I2C / SPI / GPIO", "interconnect", "register_or_state_model"),
 "network_nic": ("Ethernet / Wi-Fi NIC", "network", "packet_or_timing_model"),
 "radio_modem": ("Cellular / Bluetooth / Wi-Fi / satellite radio", "radio", "state_model_no_RF"),
 "display": ("LCD / OLED / e-ink / touch display", "input_output", "framebuffer_or_event_model"),
 "camera": ("Camera / image sensor", "sensor", "frame_or_metadata_model"),
 "audio": ("Audio codec / microphone / speaker", "input_output", "sample_or_frame_model"),
 "input_devices": ("Keyboard / mouse / touch / game controls", "input_output", "event_model"),
 "sensors": ("Motion / temperature / pressure / GPS / biometric sensors", "sensor", "synthetic_or_replay"),
 "battery": ("Battery / fuel gauge", "power", "estimate_model"),
 "power": ("PSU / PMIC / voltage regulators", "power", "estimate_model"),
 "thermal": ("Cooling / fan / thermal sensors", "thermal", "estimate_model"),
 "security": ("TPM / secure element / biometric security", "security", "software_contract_unless_documented"),
 "clock_rtc": ("Clock / RTC / timer / watchdog", "platform", "deterministic_state_model"),
 "optical_drive": ("CD / DVD / Blu-ray drive", "storage", "media_state_model"),
 "printer_engine": ("Printer / scanner / plotter engine", "office_io", "job_and_page_model"),
 "robot_actuators": ("Motors / servos / actuators", "actuation", "kinematic_or_state_model"),
 "vehicle_bus": ("CAN / LIN / automotive Ethernet", "interconnect", "message_model"),
 "medical_io": ("Medical acquisition / treatment interface", "specialized_io", "nonclinical_simulation_only"),
 "scientific_io": ("DAQ / oscilloscope / laboratory instrument I/O", "specialized_io", "sample_and_protocol_model"),
 "satellite_comms": ("Satellite telemetry / navigation / communications", "specialized_io", "link_and_message_model"),
 "enclosure": ("Chassis / enclosure / ports", "mechanical", "metadata_model"),
 "peripheral_bus": ("PCIe / USB / Thunderbolt / dock / expansion bus", "interconnect", "topology_model"),
}

def _family(name, category, examples, components):
    return {"name": name, "category": category, "examples": examples.split("|"), "components": components.split()}

DEVICE_FAMILIES = {
 "desktop_pc": _family("Desktop computer", "computing", "desktop PC|all-in-one|mini PC|HTPC|thin client", "cpu gpu ram cache motherboard chipset rom_firmware storage storage_controller pcie usb network_nic audio input_devices display power thermal clock_rtc security enclosure"),
 "laptop": _family("Laptop and notebook", "computing", "laptop|notebook|ultrabook|Chromebook|gaming laptop|2-in-1|mobile workstation", "cpu gpu npu ram cache motherboard chipset rom_firmware storage storage_controller pcie usb network_nic radio_modem display camera audio input_devices battery power thermal clock_rtc security sensors enclosure"),
 "server_workstation": _family("Server and workstation", "computing", "tower/rack/blade server|GPU/AI server|storage server|mainframe|supercomputer|workstation|cloud/virtual server", "cpu gpu npu ram cache motherboard chipset rom_firmware storage storage_controller pcie network_nic power thermal clock_rtc security enclosure"),
 "mobile_device": _family("Phone and tablet", "mobile", "Android phone|iPhone|feature phone|rugged phone|satellite phone|tablet|e-reader|handheld computer", "cpu gpu npu dsp ram cache rom_firmware storage storage_controller display camera audio input_devices radio_modem network_nic sensors battery power thermal clock_rtc security i2c_spi_gpio enclosure"),
 "game_console": _family("Game console and handheld gaming", "gaming", "PlayStation family|Xbox family|Nintendo family|Steam Deck|ROG Ally|Legion Go|arcade|retro console", "cpu gpu npu ram cache motherboard chipset rom_firmware storage storage_controller pcie usb network_nic radio_modem display audio input_devices power thermal clock_rtc security enclosure"),
 "network_appliance": _family("Networking and telecommunications", "networking", "router|modem|switch|access point|repeater|firewall|ONT|NAS|VoIP phone|base station|VPN gateway|load balancer", "cpu ram rom_firmware storage network_nic radio_modem pcie usb power thermal clock_rtc security enclosure"),
 "compute_component": _family("Compute and board components", "components", "CPU|GPU|NPU|TPU|DSP|FPGA|microcontroller|SoC|motherboard|chipset|RAM|cache|TPM|PSU|UPS|cooler|expansion card", "cpu gpu npu dsp fpga microcontroller ram cache motherboard chipset rom_firmware pcie power thermal security clock_rtc enclosure"),
 "storage_system": _family("Storage and removable media", "storage", "SATA/NVMe SSD|HDD|USB flash drive|memory card|external drive|optical drive|NAS|SAN|tape drive|RAID array", "storage storage_controller ram cache cpu rom_firmware pcie usb network_nic optical_drive power thermal clock_rtc enclosure"),
 "display_projector": _family("Display and projection", "display", "LCD/LED/OLED/QLED monitor|smart TV|touchscreen|projector|interactive whiteboard|digital signage|VR display", "display cpu gpu ram rom_firmware storage network_nic radio_modem audio input_devices power thermal clock_rtc enclosure"),
 "media_capture": _family("Audio, video, photography and streaming", "media", "DSLR/mirrorless/action camera|CCTV/IP camera|webcam|camcorder|microphone|mixer|DAC|amplifier|headphones|speaker|Blu-ray player|streaming encoder", "cpu dsp gpu ram storage rom_firmware camera audio display network_nic radio_modem usb power battery sensors clock_rtc enclosure"),
 "wearable": _family("Wearable and immersive devices", "wearable", "smartwatch|fitness tracker|smart ring|smart glasses|AR/VR/MR headset|GPS sports watch|body camera", "cpu gpu npu ram storage rom_firmware display camera audio input_devices radio_modem network_nic sensors battery power thermal clock_rtc security i2c_spi_gpio enclosure"),
 "smart_home": _family("Smart home and household electronics", "home", "smart speaker/display|smart bulb/switch/plug/lock/doorbell|thermostat|robot vacuum|refrigerator|washer|dishwasher|microwave|air conditioner/purifier|coffee machine|electronic scale", "microcontroller cpu ram rom_firmware storage network_nic radio_modem display camera audio input_devices sensors robot_actuators power thermal clock_rtc security i2c_spi_gpio enclosure"),
 "office_device": _family("Office and document devices", "office", "inkjet/laser/3D printer|scanner|multifunction printer|barcode/QR scanner|label/receipt printer|plotter|copier|laminator|document camera|conference phone", "cpu ram rom_firmware storage storage_controller network_nic usb display camera input_devices printer_engine sensors power thermal clock_rtc enclosure"),
 "vehicle_transport": _family("Vehicle and transport electronics", "transport", "ECU|infotainment|digital dashboard|GPS|dashcam|parking sensor|ADAS radar/LiDAR|TPMS|OBD-II|EV charger|e-bike/scooter controller|train/aircraft/marine computer", "cpu microcontroller dsp ram rom_firmware storage network_nic radio_modem display camera audio sensors vehicle_bus battery power thermal clock_rtc security i2c_spi_gpio enclosure"),
 "medical_device": _family("Medical and patient-monitoring equipment", "medical", "ECG/EEG|ultrasound|MRI/CT/X-ray|patient monitor|pulse oximeter|thermometer|blood pressure/glucose meter|infusion pump|ventilator|lab analyzer", "cpu gpu dsp fpga ram storage rom_firmware display camera audio sensors medical_io network_nic security power battery thermal clock_rtc i2c_spi_gpio enclosure"),
 "scientific_instrument": _family("Scientific and laboratory instrumentation", "science", "digital microscope|oscilloscope|spectrum/logic analyzer|signal generator|DAQ|programmable power supply|electronic meter|laboratory analyzer", "cpu dsp fpga ram storage rom_firmware display input_devices sensors scientific_io usb network_nic power thermal clock_rtc enclosure"),
 "robot_industrial": _family("Robotics, industrial control and IoT", "industrial", "industrial/collaborative/humanoid robot|robotic arm|AMR/warehouse/delivery/agricultural robot|CNC|PLC|SCADA controller|machine-vision camera|edge AI computer|smart meter|IoT gateway", "cpu gpu npu microcontroller fpga ram storage rom_firmware network_nic radio_modem camera sensors robot_actuators i2c_spi_gpio power thermal clock_rtc security enclosure"),
 "power_energy": _family("Power and energy electronics", "energy", "solar inverter|BMS|portable power station|smart meter|charge controller|DC-DC/AC-DC converter|VFD|relay|smart breaker|generator controller|EV charging station|PDU", "microcontroller cpu ram rom_firmware storage network_nic sensors battery power thermal clock_rtc security i2c_spi_gpio enclosure"),
 "peripheral_accessory": _family("Computer peripherals and accessories", "peripheral", "keyboard|mouse|trackball|graphics tablet|game controller|joystick|wheel controller|USB hub|dock|KVM|card reader|adapter|capture card", "microcontroller ram rom_firmware storage usb peripheral_bus network_nic display input_devices audio sensors power clock_rtc enclosure"),
 "satellite_space": _family("Satellite, navigation and space systems", "space", "satellite|satellite modem/phone|GNSS/GPS receiver|ground station|spacecraft flight computer|telemetry receiver|remote sensing payload|space robot controller", "cpu dsp fpga ram storage rom_firmware network_nic radio_modem satellite_comms display sensors robot_actuators power battery thermal clock_rtc security i2c_spi_gpio enclosure"),
 "embedded_iot": _family("Embedded and IoT modules", "embedded", "Arduino/Raspberry Pi-class board|sensor node|smart tag|development board|embedded gateway|USB/serial adapter", "microcontroller cpu ram storage rom_firmware network_nic radio_modem sensors i2c_spi_gpio usb power battery clock_rtc security enclosure"),
}

def list_component_classes():
    """Return canonical component classes in stable ID order."""
    return [{"component_id": key, "name": value[0], "kind": value[1], "fidelity_target": value[2]}
            for key, value in sorted(COMPONENT_CLASSES.items())]

def list_device_families(category=None):
    """List catalog families, optionally filtered by category."""
    return [{"family_id": key, **deepcopy(value), "component_count": len(value["components"])}
            for key, value in sorted(DEVICE_FAMILIES.items())
            if category is None or value["category"] == category]

def get_device_family(family_id):
    """Resolve a family and its typical component inventory with honest status labels."""
    if family_id not in DEVICE_FAMILIES:
        raise ValueError(f"UNKNOWN_DEVICE_FAMILY:{family_id}")
    family = deepcopy(DEVICE_FAMILIES[family_id])
    family["family_id"] = family_id
    family["component_inventory"] = [
        {"component_id": key, "name": COMPONENT_CLASSES[key][0], "kind": COMPONENT_CLASSES[key][1],
         "fidelity_target": COMPONENT_CLASSES[key][2]} for key in family["components"]]
    family["physical_hardware_required"] = False
    family["status"] = "CATALOGED_NOT_FULLY_EMULATED"
    family["limitations"] = [
        "Catalog membership does not mean a complete device or proprietary firmware is emulated.",
        "Component presence and exact specifications vary by model and SKU.",
        "Performance, power, thermal and sensor values are estimates unless calibrated.",
        "No physical hardware, RF transmission, medical treatment, vehicle actuation or external I/O is performed."]
    return family

def validate_catalog():
    missing = sorted({component for family in DEVICE_FAMILIES.values()
                      for component in family["components"] if component not in COMPONENT_CLASSES})
    duplicate_examples = {key: len(value["examples"]) - len(set(value["examples"]))
                          for key, value in DEVICE_FAMILIES.items()
                          if len(value["examples"]) != len(set(value["examples"]))}
    return {"ok": not missing and not duplicate_examples, "family_count": len(DEVICE_FAMILIES),
            "component_class_count": len(COMPONENT_CLASSES), "missing_component_references": missing,
            "duplicate_examples": duplicate_examples, "physical_hardware_required": False,
            "full_device_emulation_claimed": False}
