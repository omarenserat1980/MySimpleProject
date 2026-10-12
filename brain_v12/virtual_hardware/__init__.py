"""Brain Virtual Computer hardware layer.

Deterministic, inspectable software-defined hardware plus guest-OS contracts.
"""
from .computer import VirtualComputer
from .cpu import VirtualCPU
from .memory import VirtualRAM
from .bus import VirtualBus
from .pcie import VirtualPCIeBAR, VirtualPCIeEndpoint, VirtualPCIeFabric
from .ecc_memory import VirtualECCMemoryController
from .devices import VirtualNIC, VirtualStorage, VirtualGPU
from .disk import VirtualDisk
from .uefi import VirtualUEFI
from .x86_64 import X86_64CPU, X86UnsupportedInstruction
from .cpu_profiles import CPUProfile, get_cpu_profile, list_cpu_profiles
from .storage_profiles import StorageProfile, get_storage_profile, list_storage_profiles
from .memory_profiles import MemoryProfile, CacheHierarchy, MemoryTimingModel, get_memory_profile, list_memory_profiles
from .peripheral_profiles import GPUProfile, NICProfile, MotherboardProfile, get_gpu_profile, get_nic_profile, get_motherboard_profile
from .power_thermal import PowerThermalModel
from .os_image import OSImage, windows_server_2025_image
from .windows_server import WindowsServerVM
from .device_catalog import COMPONENT_CLASSES, DEVICE_FAMILIES, get_device_family, list_component_classes, list_device_families, validate_catalog
from .mining_hardware import ASICProfile, DEFAULT_ASIC_PROFILES, MiningFaults, MinerState, VirtualASICMiner
from .mining_farm import VirtualMiningFarm
from .network_hardware import NETWORK_DEVICE_KINDS, NetworkDevice, NetworkLink, VirtualNetworkFabric
from .software_hardware_nodes import SoftwareHardwareNode, SoftwareHardwareNodeFabric
from .extended_devices import (
    VirtualTPM, VirtualUSBController, VirtualSerialConsole, VirtualWatchdog, VirtualRNG,
    VirtualModem, VirtualBMC, VirtualIOMMU, VirtualRAID, VirtualBattery,
    VirtualInputDevice, VirtualAudioDevice, VirtualSensorHub, VirtualPeripheralFabric,
)

__all__ = [
    "VirtualComputer", "VirtualCPU", "VirtualRAM", "VirtualBus", "VirtualPCIeBAR", "VirtualPCIeEndpoint", "VirtualPCIeFabric", "VirtualECCMemoryController",
    "VirtualNIC", "VirtualStorage", "VirtualGPU", "VirtualDisk", "VirtualUEFI",
    "X86_64CPU", "X86UnsupportedInstruction", "CPUProfile", "get_cpu_profile", "list_cpu_profiles",
    "StorageProfile", "get_storage_profile", "list_storage_profiles", "MemoryProfile", "CacheHierarchy",
    "MemoryTimingModel", "get_memory_profile", "list_memory_profiles", "GPUProfile", "NICProfile",
    "MotherboardProfile", "get_gpu_profile", "get_nic_profile", "get_motherboard_profile",
    "PowerThermalModel", "OSImage", "windows_server_2025_image", "WindowsServerVM",
    "COMPONENT_CLASSES", "DEVICE_FAMILIES", "get_device_family", "list_component_classes", "list_device_families", "validate_catalog",
    "ASICProfile", "DEFAULT_ASIC_PROFILES", "MiningFaults", "MinerState", "VirtualASICMiner", "VirtualMiningFarm",
    "NETWORK_DEVICE_KINDS", "NetworkDevice", "NetworkLink", "VirtualNetworkFabric", "SoftwareHardwareNode", "SoftwareHardwareNodeFabric",
    "VirtualTPM", "VirtualUSBController", "VirtualSerialConsole", "VirtualWatchdog", "VirtualRNG",
    "VirtualModem", "VirtualBMC", "VirtualIOMMU", "VirtualRAID", "VirtualBattery",
    "VirtualInputDevice", "VirtualAudioDevice", "VirtualSensorHub", "VirtualPeripheralFabric",
]
