"""Source-backed GPU/NIC device references and synthetic motherboard topology profiles."""
from __future__ import annotations

from dataclasses import dataclass


NVIDIA_T4_SOURCE = "https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/tesla-t4/t4-tensor-core-product-brief.pdf"
INTEL_I225_SOURCE = "https://www.intel.com/content/www/us/en/products/sku/184676/intel-ethernet-controller-i225v/specifications.html"
PCISIG_GEN4_SOURCE = "https://pcisig.com/pci-express-4.0-specification"


@dataclass(frozen=True)
class GPUProfile:
    profile_id: str
    vendor: str
    model: str
    compute_units: int
    execution_lanes: int
    tensor_cores: int
    vram_capacity_bytes: int
    vram_bandwidth_bytes_per_second: int
    fp32_peak_flops_per_second: int
    pcie_generation: int
    pcie_lanes: int
    tdp_watts: float
    source_url: str
    fidelity: str = "performance_estimation"

    def describe(self) -> dict:
        return {**self.__dict__, "provenance": {"kind": "vendor_documentation", "url": self.source_url},
                "supported_emulated_api": ["Brain framebuffer API", "Brain synthetic workload descriptor"],
                "unsupported_features": ["CUDA runtime/API compatibility", "shader execution", "actual tensor-core execution",
                    "GPU driver/firmware", "physical VRAM allocation", "cycle-accurate GPU scheduling"],
                "host_gpu_acceleration": False, "performance_values_are_vendor_peaks": True,
                "physical_benchmark_measurement": False}


@dataclass(frozen=True)
class NICProfile:
    profile_id: str
    vendor: str
    model: str
    link_speed_bits_per_second: int
    max_mtu_bytes: int
    pcie_generation: int
    pcie_lanes: int
    tdp_watts: float
    source_url: str
    modeled_queue_depth: int = 256
    modeled_base_latency_us: float = 10.0
    fidelity: str = "timing_model"

    def describe(self) -> dict:
        return {**self.__dict__, "provenance": {"kind": "vendor_documentation", "url": self.source_url},
                "queue_depth_and_base_latency_are_simulator_assumptions": True,
                "unsupported_features": ["Ethernet PHY signal behavior", "MAC register protocol", "TCP/IP stack",
                    "hardware checksum/offload", "real DMA engine", "external network transmission"],
                "external_network_enabled": False, "physical_measurement": False}


@dataclass(frozen=True)
class MotherboardProfile:
    profile_id: str
    model: str
    pcie_generation: int
    total_pcie_lanes: int
    sata_ports: int
    source_url: str
    fidelity: str = "functional_topology_and_approximate_bandwidth"

    def describe(self) -> dict:
        return {**self.__dict__,
                "model_status": "synthetic motherboard topology, not a commercial board model",
                "provenance": {"kind": "derived_from_pcie_generation_reference", "url": self.source_url},
                "unsupported_features": ["electrical signaling", "equalization/training", "real switch silicon",
                    "PCIe TLP/DLLP packet protocol", "hardware IOMMU enforcement", "real hot-plug signaling"],
                "physical_measurement": False}


GPU_PROFILES = {
    "nvidia-tesla-t4": GPUProfile(
        "nvidia-tesla-t4", "NVIDIA", "Tesla T4", 40, 2560, 320,
        16_000_000_000, 320_000_000_000, 8_100_000_000_000, 3, 16, 70.0,
        NVIDIA_T4_SOURCE,
    ),
}

NIC_PROFILES = {
    "intel-i225-v": NICProfile(
        "intel-i225-v", "Intel", "Ethernet Controller I225-V", 2_500_000_000,
        9000, 2, 1, 1.95, INTEL_I225_SOURCE,
    ),
}

MOTHERBOARD_PROFILES = {
    "brain-pcie-gen4-x24": MotherboardProfile(
        "brain-pcie-gen4-x24", "Brain synthetic PCIe Gen4 x24 topology",
        4, 24, 4, PCISIG_GEN4_SOURCE,
    ),
    "brain-pcie-gen3-x20": MotherboardProfile(
        "brain-pcie-gen3-x20", "Brain synthetic PCIe Gen3 x20 topology",
        3, 20, 4, PCISIG_GEN4_SOURCE,
    ),
}


def get_gpu_profile(profile_id: str) -> GPUProfile:
    try:
        return GPU_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_GPU_PROFILE:{profile_id}") from exc


def get_nic_profile(profile_id: str) -> NICProfile:
    try:
        return NIC_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_NIC_PROFILE:{profile_id}") from exc


def get_motherboard_profile(profile_id: str) -> MotherboardProfile:
    try:
        return MOTHERBOARD_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_MOTHERBOARD_PROFILE:{profile_id}") from exc
