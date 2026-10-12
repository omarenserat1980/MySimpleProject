from __future__ import annotations
from dataclasses import dataclass, replace
import base64
import hashlib
import json
from .cpu import VirtualCPU
from .x86_64 import X86_64CPU
from .cpu_profiles import get_cpu_profile
from .storage_profiles import get_storage_profile
from .memory_profiles import get_memory_profile, CacheHierarchy
from .peripheral_profiles import (get_gpu_profile, get_nic_profile, get_motherboard_profile)
from .power_thermal import PowerThermalModel
from .memory import VirtualRAM
from .bus import VirtualBus
from .devices import VirtualNIC,VirtualStorage,VirtualGPU
from .hardware_profiles import (MachineManifest, synthetic_baseline_profiles, HardwareProfile,
                                FidelityLevel, SpecificationSource, ProvenanceKind)
from .firmware import VirtualFirmware
from .kernel import VirtualKernel
from .filesystem import VirtualFilesystem
from .bootloader import VirtualBootloader
from ..brain.self_trust_boot_gate import BootGateEvidence, evaluate

@dataclass
class VirtualComputer:
    """Software-defined computer with an optional Brain self-trust boot gate."""
    name: str
    ram_size: int = 65536
    storage_size: int | None = None
    gpu_width: int = 320
    gpu_height: int = 200
    cpu_profile_id: str | None = None
    storage_profile_id: str | None = None
    ram_profile_id: str | None = None
    cache_enabled: bool = False
    memory_channels: int = 1
    memory_channel_width_bits: int = 64
    configured_cas_latency_cycles: int | None = None
    gpu_profile_id: str | None = None
    nic_profile_id: str | None = None
    motherboard_profile_id: str | None = "brain-pcie-gen4-x24"
    external_network_enabled: bool = False

    def __post_init__(self):
        self.cpu = X86_64CPU(profile_id=self.cpu_profile_id) if self.cpu_profile_id else VirtualCPU()
        self.ram=VirtualRAM(self.ram_size, profile_id=self.ram_profile_id, channels=self.memory_channels,
                            channel_width_bits=self.memory_channel_width_bits,
                            configured_cas_latency_cycles=self.configured_cas_latency_cycles,
                            cache_enabled=self.cache_enabled)
        self.bus=VirtualBus(profile_id=self.motherboard_profile_id)
        self.storage=VirtualStorage(capacity=self.storage_size, profile_id=self.storage_profile_id)
        self.nic=VirtualNIC(profile_id=self.nic_profile_id, external_network_enabled=self.external_network_enabled)
        self.gpu=VirtualGPU(self.gpu_width,self.gpu_height,profile_id=self.gpu_profile_id)
        self.nic.attach_bus(self.bus)
        self.gpu.attach_bus(self.bus)
        self.firmware=VirtualFirmware()
        self.kernel=VirtualKernel()
        self.filesystem=VirtualFilesystem(self.storage)
        self.bootloader=VirtualBootloader()
        for n,d in [("cpu",self.cpu),("ram",self.ram),("storage",self.storage),("nic",self.nic),("gpu",self.gpu)]:
            self.bus.attach(n,d)
        self.powered=False
        self.boot_count=0
        self.boot_record=None
        self.power_thermal=PowerThermalModel()
        self._checkpoint_resume=False

    def power_on(self, boot_evidence: BootGateEvidence | None = None):
        if boot_evidence is not None:
            gate=evaluate(boot_evidence)
            if not gate.ok:
                self.powered=False
                self.boot_record={"ok":False,"status":gate.status,"boot_gate":gate.__dict__}
                raise RuntimeError("BRAIN_BOOT_BLOCKED")
        self.powered=True
        self.boot_count+=1
        self.cpu.reset()
        self.kernel.reset()
        self.boot_record=self.firmware.boot(self)
        self.boot_record["bootloader"]=self.bootloader.load(self)
        if not self.boot_record["bootloader"].get("ok"):
            self.powered=False
            raise RuntimeError("BOOTLOADER_FAILED")
        if not self.boot_record.get("ok"):
            self.powered=False
            raise RuntimeError("FIRMWARE_BOOT_FAILED")
        if boot_evidence is not None:
            self.boot_record["boot_gate"]={"ok":True,"status":"BRAIN_READY","task_id":boot_evidence.task_id}
        return self.status()

    def power_off(self):
        self.powered=False
        return self.status()

    def execute(self,program,max_cycles:int=10000):
        if not self.powered: raise RuntimeError("COMPUTER_POWER_OFF")
        if isinstance(self.cpu, X86_64CPU):
            return self.cpu.run(program, max_cycles)
        return self.cpu.run(program,self.ram,max_cycles)

    def create_process(self,name):
        if not self.powered: raise RuntimeError("COMPUTER_POWER_OFF")
        return self.kernel.create_process(name)

    def syscall(self,pid,name,**args):
        if not self.powered: raise RuntimeError("COMPUTER_POWER_OFF")
        return self.kernel.syscall(pid,name,**args)

    def hardware_manifest(self):
        """Describe existing devices and their declared fidelity; allocates no host resources."""
        profiles = []
        for profile in synthetic_baseline_profiles():
            parameters = dict(profile.parameters)
            if profile.category == "memory":
                parameters["default_addressable_cells"] = self.ram.size
            elif profile.category == "storage":
                parameters["default_capacity_bytes"] = self.storage.capacity
            elif profile.category == "gpu":
                parameters["default_width"] = self.gpu.width
                parameters["default_height"] = self.gpu.height
            elif profile.category == "network":
                parameters["mac"] = self.nic.mac
            if profile.category == "memory" and self.ram_profile_id:
                selected_memory = get_memory_profile(self.ram_profile_id)
                memory_description = selected_memory.describe(self.memory_channels, self.memory_channel_width_bits,
                                                               self.ram.timing_model.configured_cas_latency_cycles if self.ram.timing_model else self.configured_cas_latency_cycles)
                profiles.append(HardwareProfile(
                    selected_memory.profile_id, "memory", selected_memory.model, FidelityLevel.TIMING_MODEL,
                    {"logical_capacity_cells": self.ram.size, "capacity_unit": "addressable_cells",
                     "technology": selected_memory.technology, "transfer_rate_mt_s": selected_memory.transfer_rate_mt_s,
                     "channels": self.memory_channels, "channel_width_bits": self.memory_channel_width_bits,
                     "peak_theoretical_bandwidth_bytes_per_second": memory_description["peak_theoretical_bandwidth_bytes_per_second"],
                     "cas_latency_cycles": memory_description["cas_latency_cycles"],
                     "cas_latency_ns_estimate": memory_description["cas_latency_ns_estimate"],
                     "host_payload_bytes_estimate": self.ram.host_payload_bytes_estimate,
                     "host_full_capacity_buffer_allocated": False},
                    ("sparse addressable cells", "analytical CAS and transfer-time estimate",
                     "request queue and bank-contention estimate"),
                    tuple(memory_description["unsupported_features"]),
                    (SpecificationSource(ProvenanceKind.VENDOR_DOCUMENTATION, selected_memory.source_url,
                     selected_memory.source_note),),
                    ("test_real_spec_profiles_and_analytical_bandwidth",
                     "test_sparse_capacity_does_not_allocate_full_host_buffer",
                     "test_memory_timing_queue_and_bank_contention"),
                ))
            elif profile.category == "storage" and self.storage_profile_id:
                selected_storage = get_storage_profile(self.storage_profile_id)
                storage_description = selected_storage.describe()
                profiles.append(HardwareProfile(
                    selected_storage.profile_id, "storage", selected_storage.model, FidelityLevel.TIMING_MODEL,
                    {"interface": selected_storage.interface, "logical_capacity_bytes": self.storage.capacity,
                     "reference_capacity_bytes": selected_storage.capacity_bytes,
                     "block_size_bytes": selected_storage.block_size_bytes,
                     "max_queue_depth_model": selected_storage.max_queue_depth,
                     "sequential_read_bytes_per_second_vendor_max": selected_storage.sequential_read_bytes_per_second,
                     "sequential_write_bytes_per_second_vendor_max": selected_storage.sequential_write_bytes_per_second,
                     "endurance_tbw_reference": selected_storage.endurance_tbw,
                     "host_disk_allocation_bytes": 0},
                    ("logical capacity and quota", "deterministic modeled queue depth",
                     "estimated latency from published throughput/IOPS points", "flush/restart durability state",
                     "logical TRIM", "SMART-style modeled counters"),
                    tuple(storage_description["unsupported_features"]),
                    (SpecificationSource(ProvenanceKind.VENDOR_DOCUMENTATION, selected_storage.source_url,
                     "Published vendor maxima are references, not simulated or measured results."),),
                    ("test_documented_profiles_have_vendor_sources_and_explicit_fidelity",
                     "test_queue_depth_and_estimated_latency_are_deterministic",
                     "test_write_back_flush_and_restart_recovery"),
                ))
            elif profile.category == "gpu" and self.gpu_profile_id:
                selected_gpu = get_gpu_profile(self.gpu_profile_id)
                gpu_description = selected_gpu.describe()
                profiles.append(HardwareProfile(
                    selected_gpu.profile_id, "gpu", selected_gpu.model, FidelityLevel.PERFORMANCE_ESTIMATION,
                    {"compute_units": selected_gpu.compute_units, "execution_lanes": selected_gpu.execution_lanes,
                     "tensor_cores": selected_gpu.tensor_cores, "logical_vram_capacity_bytes": self.gpu.logical_vram_capacity_bytes,
                     "vram_bandwidth_bytes_per_second_vendor_peak": selected_gpu.vram_bandwidth_bytes_per_second,
                     "fp32_peak_flops_per_second_vendor_peak": selected_gpu.fp32_peak_flops_per_second,
                     "pcie_generation": selected_gpu.pcie_generation, "pcie_lanes": selected_gpu.pcie_lanes,
                     "tdp_watts_reference": selected_gpu.tdp_watts, "host_gpu_acceleration": False},
                    ("framebuffer API", "logical VRAM quota", "command queue", "synchronization",
                     "analytical FP32 throughput estimate", "modeled transfer bandwidth"),
                    tuple(gpu_description["unsupported_features"]),
                    (SpecificationSource(ProvenanceKind.VENDOR_DOCUMENTATION, selected_gpu.source_url,
                     "Vendor peak specifications are reference values, not simulated or measured throughput."),),
                    ("test_gpu_profile_metadata_and_logical_vram",
                     "test_gpu_queue_and_deterministic_throughput_estimate"),
                ))
            elif profile.category == "network" and self.nic_profile_id:
                selected_nic = get_nic_profile(self.nic_profile_id)
                nic_description = selected_nic.describe()
                profiles.append(HardwareProfile(
                    selected_nic.profile_id, "network", selected_nic.model, FidelityLevel.TIMING_MODEL,
                    {"link_speed_bits_per_second": selected_nic.link_speed_bits_per_second,
                     "mtu_bytes": self.nic.mtu, "pcie_generation": selected_nic.pcie_generation,
                     "pcie_lanes": selected_nic.pcie_lanes, "tdp_watts_reference": selected_nic.tdp_watts,
                     "queue_depth_model": self.nic.queue_depth, "external_network_enabled": self.external_network_enabled},
                    ("packet queues", "MTU enforcement", "estimated serialization latency",
                     "interrupt moderation", "modeled DMA accounting", "backpressure"),
                    tuple(nic_description["unsupported_features"]),
                    (SpecificationSource(ProvenanceKind.VENDOR_DOCUMENTATION, selected_nic.source_url,
                     "Device link speed is vendor specified; timing/queue behavior remains modeled."),),
                    ("test_nic_packet_queues_mtu_and_backpressure",
                     "test_nic_profile_uses_no_external_network"),
                ))
            elif profile.category == "bus" and self.motherboard_profile_id:
                topology = self.bus.validate_topology()
                profiles.append(HardwareProfile(
                    "brain-bus-topology-" + self.motherboard_profile_id, "bus",
                    "Brain PCIe lane allocator and DMA/interrupt event model", FidelityLevel.TIMING_MODEL,
                    {"motherboard_profile_id": self.motherboard_profile_id,
                     "pcie_lanes_allocated": topology["pcie_lanes_allocated"],
                     "pcie_lanes_total": topology["pcie_lanes_total"],
                     "sata_ports_allocated": topology["sata_ports_allocated"],
                     "topology_valid": topology["ok"], "electrical_fidelity": False},
                    ("device enumeration", "lane allocation and generation negotiation",
                     "topology validation", "DMA transfer accounting", "interrupt routing",
                     "virtual reset and hot-plug"),
                    ("PCIe TLP/DLLP protocol", "electrical signaling", "real IOMMU", "hardware-compatible hot-plug"),
                    (SpecificationSource(ProvenanceKind.DERIVED, get_motherboard_profile(self.motherboard_profile_id).source_url,
                     "Derived topology profile; no commercial motherboard is emulated."),),
                    ("test_topology_lane_budget_and_dma_accounting",
                     "test_topology_conflict_rejected_before_boot"),
                ))
            elif profile.category == "cpu" and self.cpu_profile_id:
                selected = get_cpu_profile(self.cpu_profile_id)
                source_kind = (ProvenanceKind.SYNTHETIC_BASELINE if selected.vendor == "Electronic Brain"
                               else ProvenanceKind.VENDOR_DOCUMENTATION)
                profiles.append(HardwareProfile(
                    selected.profile_id, "cpu", selected.model, FidelityLevel.FUNCTIONAL,
                    selected.specification_parameters, selected.modeled_behaviors,
                    selected.unsupported_features,
                    tuple(SpecificationSource(source_kind, url, "Reference metadata; not proof of ISA conformance.")
                          for url in selected.specification_urls),
                    selected.conformance_tests,
                ))
            else:
                profiles.append(replace(profile, parameters=parameters))
        if self.cache_enabled:
            profiles.append(HardwareProfile(
                "brain-l1-l2-l3-tag-model-v1", "cache", "Brain synthetic L1/L2/L3 tag hierarchy",
                FidelityLevel.TIMING_MODEL,
                {"levels": [{"name": level.name, "size_bytes": level.size_bytes,
                             "line_size_bytes": level.line_size_bytes, "associativity": level.associativity,
                             "hit_latency_cycles": level.hit_latency_cycles}
                            for level in self.ram.cache_hierarchy.levels]},
                ("set-associative tags", "LRU replacement", "hit/miss counters", "approximate hit latency"),
                ("cache data storage", "coherence", "MESI/MOESI", "prefetching", "cycle-accurate arbitration"),
                (SpecificationSource(ProvenanceKind.SYNTHETIC_BASELINE,
                                     "brain://virtual-hardware/cache-tag-model-v1",
                                     "Synthetic cache geometry for deterministic tests, not a claim about a named CPU."),),
                ("test_l1_l2_l3_tag_model_and_deterministic_hits",),
            ))
        if self.motherboard_profile_id:
            board = get_motherboard_profile(self.motherboard_profile_id)
            board_description = board.describe()
            profiles.append(HardwareProfile(
                board.profile_id, "motherboard", board.model, FidelityLevel.TIMING_MODEL,
                {"pcie_generation": board.pcie_generation, "total_pcie_lanes": board.total_pcie_lanes,
                 "sata_ports": board.sata_ports, "device_count": len(self.bus.devices)},
                ("synthetic slot/lane topology", "capacity validation", "virtual hot-plug/reset"),
                tuple(board_description["unsupported_features"]),
                (SpecificationSource(ProvenanceKind.DERIVED, board.source_url,
                 "PCIe generation reference only; topology is synthetic, not a real motherboard specification."),),
                ("test_topology_lane_budget_and_dma_accounting", "test_topology_conflict_rejected_before_boot"),
            ))
        profiles.append(HardwareProfile(
            "brain-virtual-firmware-v1", "firmware", "Brain deterministic virtual firmware and bootloader",
            FidelityLevel.FUNCTIONAL,
            {"firmware_version": self.firmware.VERSION, "bootloader_version": self.bootloader.VERSION,
             "kernel_required": False},
            ("device enumeration", "boot record", "optional kernel image check", "manifest-gated boot"),
            ("physical BIOS/UEFI execution", "ACPI tables", "secure-boot cryptographic chain"),
            (SpecificationSource(ProvenanceKind.SYNTHETIC_BASELINE,
                                 "brain://virtual-hardware/firmware-v1",
                                 "Software firmware contract, not a vendor firmware implementation."),),
            ("test_machine_manifest_v2_includes_firmware_power_thermal",),
            units={"firmware_version": "version string", "bootloader_version": "version string"},
        ))
        known_tdp = {}
        if self.cpu_profile_id:
            cpu_ref = get_cpu_profile(self.cpu_profile_id).specification_parameters
            if cpu_ref.get("tdp_watts") is not None:
                known_tdp["cpu"] = cpu_ref["tdp_watts"]
        if self.gpu_profile_id:
            known_tdp["gpu"] = get_gpu_profile(self.gpu_profile_id).tdp_watts
        if self.nic_profile_id:
            known_tdp["nic"] = get_nic_profile(self.nic_profile_id).tdp_watts
        profiles.append(HardwareProfile(
            "brain-power-estimate-v1", "power", "Brain synthetic load-to-power estimate",
            FidelityLevel.PERFORMANCE_ESTIMATION,
            {"modelled_idle_watts": self.power_thermal.idle_power_watts,
             "modelled_peak_watts": self.power_thermal.peak_power_watts,
             "known_vendor_tdp_references": known_tdp,
             "known_vendor_tdp_sum_watts": sum(known_tdp.values()),
             "tdp_sum_is_complete_system_power": False,
             "calibrated": False},
            ("load-fraction to estimated watts", "vendor TDP reference reporting", "thermal-model input"),
            ("physical current/voltage measurement", "component-level transient power", "calibrated wall-power prediction"),
            (SpecificationSource(ProvenanceKind.SYNTHETIC_BASELINE,
                                 "brain://virtual-hardware/power-estimate-v1",
                                 "Idle/peak power values are configurable synthetic defaults; vendor TDP references are reported separately."),),
            ("test_power_thermal_estimates_and_throttling",),
            units={"modelled_idle_watts": "W", "modelled_peak_watts": "W",
                   "known_vendor_tdp_sum_watts": "W"},
        ))
        profiles.append(HardwareProfile(
            "brain-thermal-rc-v1", "thermal", "Brain lumped thermal RC estimate",
            FidelityLevel.TIMING_MODEL,
            {"ambient_c": self.power_thermal.ambient_c,
             "thermal_capacity_j_per_c": self.power_thermal.thermal_capacity_j_per_c,
             "cooling_w_per_c": self.power_thermal.cooling_w_per_c,
             "throttle_c": self.power_thermal.throttle_c, "shutdown_c": self.power_thermal.shutdown_c,
             "fan_curve": "piecewise-linear synthetic curve"},
            ("thermal inertia", "cooling effectiveness", "fan curve estimate", "throttling", "cool-down recovery", "fault injection"),
            ("physical temperature sensor", "calibrated chassis thermal dynamics", "component hotspot CFD"),
            (SpecificationSource(ProvenanceKind.SYNTHETIC_BASELINE,
                                 "brain://virtual-hardware/thermal-rc-v1",
                                 "Synthetic lumped RC parameters, not measured device thermals."),),
            ("test_power_thermal_estimates_and_throttling", "test_thermal_fault_and_recovery"),
            units={"ambient_c": "degC", "thermal_capacity_j_per_c": "J/degC",
                   "cooling_w_per_c": "W/degC", "throttle_c": "degC", "shutdown_c": "degC"},
        ))
        required = ("cpu", "memory", "bus", "storage", "network", "motherboard", "firmware", "power", "thermal")
        return MachineManifest(self.name, 2, tuple(profiles), required_categories=required).describe()

    def status(self):
        return {"name":self.name,"powered":self.powered,"boot_count":self.boot_count,
                "firmware":{"version":self.firmware.VERSION,"booted":bool(self.boot_record and self.boot_record.get("ok"))},
                "bootloader":self.bootloader.VERSION,
                "filesystem":{"files":len(self.storage.files)},
                "kernel":self.kernel.status(),
                "cpu":{"pc":self.cpu.registers["RIP"] if isinstance(self.cpu, X86_64CPU) else self.cpu.pc,"cycles":self.cpu.cycles,"halted":self.cpu.halted,"profile_id":self.cpu_profile_id or "brain-educational-8-register"},
                "ram":self.ram.status(),"devices":self.bus.device_names(),
                "storage":{"capacity":self.storage.capacity,"files":len(self.storage.files)},
                "network":self.nic.status(),"gpu":self.gpu.status(),"bus":self.bus.status()}
