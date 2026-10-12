"""Brain Virtual Computer hardware layer.

Deterministic, inspectable software-defined hardware plus guest-OS contracts.
"""
from .computer import VirtualComputer
from .cpu import VirtualCPU
from .memory import VirtualRAM
from .bus import VirtualBus
from .devices import VirtualNIC, VirtualStorage, VirtualGPU
from .disk import VirtualDisk
from .uefi import VirtualUEFI
from .x86_64 import X86_64CPU, X86UnsupportedInstruction
from .cpu_profiles import CPUProfile, get_cpu_profile, list_cpu_profiles
from .storage_profiles import StorageProfile, get_storage_profile, list_storage_profiles
from .memory_profiles import MemoryProfile, CacheHierarchy, MemoryTimingModel, get_memory_profile, list_memory_profiles
from .peripheral_profiles import GPUProfile, NICProfile, MotherboardProfile, get_gpu_profile, get_nic_profile, get_motherboard_profile
from .os_image import OSImage, windows_server_2025_image
from .windows_server import WindowsServerVM

__all__ = [
    "VirtualComputer","VirtualCPU","VirtualRAM","VirtualBus",
    "VirtualNIC","VirtualStorage","VirtualGPU","VirtualDisk","VirtualUEFI",
    "X86_64CPU","X86UnsupportedInstruction","CPUProfile","get_cpu_profile","list_cpu_profiles","StorageProfile","get_storage_profile","list_storage_profiles","MemoryProfile","CacheHierarchy","MemoryTimingModel","get_memory_profile","list_memory_profiles","GPUProfile","NICProfile","MotherboardProfile","get_gpu_profile","get_nic_profile","get_motherboard_profile","OSImage","windows_server_2025_image","WindowsServerVM"
]
