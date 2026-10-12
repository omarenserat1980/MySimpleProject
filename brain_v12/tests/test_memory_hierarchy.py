from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.memory_profiles import (
    CacheHierarchy, MemoryTimingModel, get_memory_profile, list_memory_profiles,
)
from brain_v12.virtual_hardware.memory import VirtualRAM
from brain_v12.virtual_hardware.computer import VirtualComputer
from brain_v12.blade_server import BladeChassis
from brain_v12.brain.resource_manager import ResourceManager


class MemoryHierarchyTests(unittest.TestCase):
    def test_real_spec_profiles_have_source_and_analytical_bandwidth(self):
        profiles = {p["profile_id"]: p for p in list_memory_profiles()}
        ddr4 = profiles["micron-ddr4-3200-x8"]
        ddr5 = profiles["micron-ddr5-5600-x16"]
        lpddr = profiles["micron-lpddr5x-8533-x64"]
        self.assertEqual(ddr4["transfer_rate_mt_s"], 3200)
        self.assertEqual(ddr4["cas_latency_cycles"], 22)
        self.assertEqual(ddr5["cas_latency_cycles"], 46)
        self.assertEqual(lpddr["transfer_rate_mt_s"], 8533)
        self.assertIsNone(lpddr["cas_latency_cycles"])
        self.assertTrue(ddr4["source_url"].startswith("https://"))
        self.assertEqual(ddr4["peak_theoretical_bandwidth_bytes_per_second"], 25_600_000_000)
        self.assertEqual(ddr5["peak_theoretical_bandwidth_bytes_per_second"], 44_800_000_000)
        self.assertFalse(lpddr["physical_measurement"])

    def test_sparse_capacity_does_not_allocate_full_host_buffer(self):
        ram = VirtualRAM(10**9)
        self.assertEqual(len(ram._data), 10**9)
        self.assertEqual(ram.used_cells, 0)
        self.assertFalse(ram.status()["host_buffer_allocated_for_full_capacity"])
        ram.write(999_999_999, 123)
        self.assertEqual(ram.read(999_999_999), 123)
        self.assertEqual(ram.used_cells, 1)

    def test_address_boundaries_and_legacy_snapshot_roundtrip(self):
        ram = VirtualRAM(8)
        ram.write(7, 255)
        snapshot = ram.snapshot()
        self.assertEqual(set(snapshot), {"size", "nonzero", "ecc_enabled"})
        restored = VirtualRAM(8)
        restored.restore(snapshot)
        self.assertEqual(restored.read(7), 255)
        with self.assertRaisesRegex(IndexError, "RAM_ADDRESS_OUT_OF_RANGE"):
            ram.read(8)
        with self.assertRaisesRegex(IndexError, "RAM_ADDRESS_OUT_OF_RANGE"):
            ram.write(-1, 2)
        with self.assertRaisesRegex(ValueError, "RAM_SIZE_MISMATCH"):
            restored.restore({"size": 9, "nonzero": {}})

    def test_memory_timing_queue_and_bank_contention(self):
        model = MemoryTimingModel(get_memory_profile("micron-ddr4-3200-x8"), max_outstanding=4)
        first = model.begin_access(0, 64, "read")
        second = model.begin_access(0, 64, "write")
        self.assertFalse(first["bank_conflict"])
        self.assertTrue(second["bank_conflict"])
        self.assertGreater(second["estimated_latency_ns"], first["estimated_latency_ns"])
        model.complete_access(first["token"])
        model.complete_access(second["token"])
        report = model.snapshot()
        self.assertEqual(report["accesses"], 2)
        self.assertEqual(report["bytes_transferred"], 128)
        self.assertEqual(report["contention_events"], 1)
        self.assertFalse(report["physical_measurement"])

    def test_l1_l2_l3_tag_model_has_deterministic_hits_and_misses(self):
        cache = CacheHierarchy()
        first = cache.access(0)
        second = cache.access(0)
        self.assertEqual(first["hit_level"], "DRAM")
        self.assertEqual(second["hit_level"], "L1")
        self.assertTrue(second["timing_is_approximate"])
        report = cache.snapshot()
        self.assertEqual([level["name"] for level in report["levels"]], ["L1", "L2", "L3"])
        self.assertEqual(report["levels"][0]["hits"], 1)
        self.assertEqual(report["levels"][0]["misses"], 1)
        self.assertFalse(report["coherence_modeled"])

    def test_ram_access_integrates_optional_cache_and_dram_profiles(self):
        ram = VirtualRAM(256, profile_id="micron-ddr5-5600-x16", cache_enabled=True)
        ram.write(4, 77)
        self.assertEqual(ram.read(4), 77)
        status = ram.status()
        self.assertEqual(status["dram_timing"]["technology"], "DDR5")
        self.assertEqual(status["cache_hierarchy"]["levels"][0]["hits"], 1)
        self.assertGreater(status["dram_timing"]["bytes_transferred"], 0)

    def test_virtual_computer_manifest_declares_memory_and_synthetic_cache(self):
        computer = VirtualComputer("memory-profiled", ram_size=10**8,
                                   ram_profile_id="micron-lpddr5x-8533-x64", cache_enabled=True)
        report = computer.hardware_manifest()
        memory = next(item for item in report["components"] if item["category"] == "memory")
        cache = next(item for item in report["components"] if item["category"] == "cache")
        self.assertEqual(memory["profile_id"], "micron-lpddr5x-8533-x64")
        self.assertEqual(memory["parameters"]["logical_capacity_cells"], 10**8)
        self.assertEqual(memory["parameters"]["cas_latency_cycles"], 32)
        self.assertEqual(cache["profile_id"], "brain-l1-l2-l3-tag-model-v1")
        self.assertEqual(computer.ram.used_cells, 0)

    def test_blade_can_select_dram_profile_and_cache(self):
        chassis = BladeChassis("profiled-memory-blade")
        blade = chassis.create_blade(ram_size=10**7, ram_profile_id="micron-ddr4-3200-x8", cache_enabled=True)
        self.assertEqual(blade.computer.ram.profile_id, "micron-ddr4-3200-x8")
        manifest = blade.computer.hardware_manifest()
        self.assertIn("cache", manifest["validation"]["categories"])
        self.assertEqual(blade.computer.ram.status()["dram_timing"]["technology"], "DDR4")

    def test_resource_accounting_does_not_scan_or_allocate_logical_capacity(self):
        chassis = BladeChassis("sparse-ram")
        blade = chassis.create_blade(ram_size=10**8)
        resources = ResourceManager().snapshot(blade)
        self.assertEqual(resources["ram"]["used_cells"], 0)
        self.assertEqual(resources["ram"]["total_bytes"], 10**8)
        self.assertEqual(resources["ram"]["capacity_unit"], "addressable_cells")
        self.assertFalse(resources["ram"]["host_rss_measured"])


if __name__ == "__main__":
    unittest.main()
