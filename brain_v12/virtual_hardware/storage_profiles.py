"""Documented SSD reference profiles. Performance fields are vendor maxima, not simulator results."""
from __future__ import annotations

from dataclasses import dataclass


SAMSUNG_870_EVO_DATASHEET = "https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_SSD_870_EVO_Data_Sheet_Rev1.1_230509.pdf"
SAMSUNG_990_PRO_DATASHEET = "https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_NVMe_SSD_990_PRO_Datasheet_Rev.1.0_10119997003518.pdf"


@dataclass(frozen=True)
class StorageProfile:
    profile_id: str
    vendor: str
    model: str
    interface: str
    capacity_bytes: int
    block_size_bytes: int
    max_queue_depth: int
    sequential_read_bytes_per_second: int
    sequential_write_bytes_per_second: int
    random_read_iops_qd1: int
    random_write_iops_qd1: int
    random_read_iops_qd32: int
    random_write_iops_qd32: int
    endurance_tbw: int
    cache_bytes: int
    trim_supported: bool
    smart_supported: bool
    source_url: str
    fidelity: str = "timing_model"
    notes: tuple[str, ...] = ()

    def describe(self) -> dict:
        return {
            **self.__dict__,
            "fidelity": self.fidelity,
            "provenance": {"kind": "vendor_datasheet", "url": self.source_url},
            "performance_values_are_vendor_maxima": True,
            "simulated_results_are_measurements": False,
            "unsupported_features": [
                "NAND flash translation layer and garbage collection internals",
                "controller firmware and physical media timing",
                "real SMART command protocol",
                "host block-device access and physical durability",
                "device-specific latency distributions not published in the cited datasheet",
            ],
        }


STORAGE_PROFILES: dict[str, StorageProfile] = {
    "samsung-870-evo-1tb": StorageProfile(
        profile_id="samsung-870-evo-1tb", vendor="Samsung", model="870 EVO 1TB",
        interface="SATA 6 Gb/s", capacity_bytes=1_000_000_000_000, block_size_bytes=4096,
        max_queue_depth=32, sequential_read_bytes_per_second=560_000_000,
        sequential_write_bytes_per_second=530_000_000, random_read_iops_qd1=13_000,
        random_write_iops_qd1=36_000, random_read_iops_qd32=98_000,
        random_write_iops_qd32=88_000, endurance_tbw=600, cache_bytes=2_000_000_000,
        trim_supported=True, smart_supported=True, source_url=SAMSUNG_870_EVO_DATASHEET,
        notes=("1TB model; DRAM cache listed as 2GB LPDDR4 in datasheet.",
               "Vendor throughput and IOPS are maxima under stated test conditions."),
    ),
    "samsung-990-pro-1tb": StorageProfile(
        profile_id="samsung-990-pro-1tb", vendor="Samsung", model="990 PRO 1TB",
        interface="PCIe Gen 4.0 x4 / NVMe 2.0", capacity_bytes=1_000_000_000_000,
        block_size_bytes=4096, max_queue_depth=64, sequential_read_bytes_per_second=7_450_000_000,
        sequential_write_bytes_per_second=6_900_000_000, random_read_iops_qd1=22_000,
        random_write_iops_qd1=80_000, random_read_iops_qd32=1_200_000,
        random_write_iops_qd32=1_550_000, endurance_tbw=600, cache_bytes=1_000_000_000,
        trim_supported=True, smart_supported=True, source_url=SAMSUNG_990_PRO_DATASHEET,
        notes=("1TB model; DRAM cache listed as 1GB LPDDR4.",
               "Vendor throughput and IOPS are maxima under stated test conditions."),
    ),
}


def get_storage_profile(profile_id: str) -> StorageProfile:
    try:
        return STORAGE_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_STORAGE_PROFILE:{profile_id}") from exc


def list_storage_profiles() -> list[dict]:
    return [STORAGE_PROFILES[key].describe() for key in sorted(STORAGE_PROFILES)]
