from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.devices import VirtualStorage
from brain_v12.virtual_hardware.storage_profiles import get_storage_profile, list_storage_profiles
from brain_v12.virtual_hardware.computer import VirtualComputer
from brain_v12.blade_server import BladeChassis
from brain_v12.virtual_hardware.storage_benchmark import run_storage_workload_benchmark


class StorageProfileTests(unittest.TestCase):
    def test_documented_profiles_have_vendor_sources_and_explicit_fidelity(self):
        profiles = {p["profile_id"]: p for p in list_storage_profiles()}
        self.assertIn("samsung-870-evo-1tb", profiles)
        self.assertIn("samsung-990-pro-1tb", profiles)
        sata = profiles["samsung-870-evo-1tb"]
        nvme = profiles["samsung-990-pro-1tb"]
        self.assertEqual(sata["interface"], "SATA 6 Gb/s")
        self.assertEqual(nvme["interface"], "PCIe Gen 4.0 x4 / NVMe 2.0")
        self.assertEqual(sata["sequential_read_bytes_per_second"], 560_000_000)
        self.assertEqual(nvme["sequential_read_bytes_per_second"], 7_450_000_000)
        self.assertTrue(sata["provenance"]["url"].startswith("https://"))
        self.assertFalse(nvme["simulated_results_are_measurements"])

    def test_logical_capacity_does_not_allocate_a_host_disk_image(self):
        disk = VirtualStorage(profile_id="samsung-990-pro-1tb")
        self.assertEqual(disk.logical_capacity_bytes, 1_000_000_000_000)
        self.assertEqual(disk.smart_telemetry()["host_disk_allocation_bytes"], 0)
        self.assertEqual(disk.smart_telemetry()["in_process_payload_bytes"], 0)

    def test_storage_profile_integrates_with_virtual_computer_manifest(self):
        computer = VirtualComputer("nvme-node", storage_profile_id="samsung-990-pro-1tb")
        manifest = computer.hardware_manifest()
        storage = next(item for item in manifest["components"] if item["category"] == "storage")
        self.assertEqual(storage["profile_id"], "samsung-990-pro-1tb")
        self.assertEqual(storage["fidelity"], "timing_model")
        self.assertEqual(storage["parameters"]["host_disk_allocation_bytes"], 0)
        self.assertEqual(computer.storage.logical_capacity_bytes, 1_000_000_000_000)

    def test_blade_creation_can_select_storage_profile_without_host_device(self):
        chassis = BladeChassis("storage-profile-test")
        blade = chassis.create_blade(storage_profile_id="samsung-870-evo-1tb")
        self.assertEqual(blade.computer.storage.profile_id, "samsung-870-evo-1tb")
        self.assertEqual(blade.computer.storage.smart_telemetry()["host_disk_allocation_bytes"], 0)

    def test_legacy_memory_storage_api_remains_compatible(self):
        disk = VirtualStorage(64)
        disk.write("/boot/kernel.bin", b"kernel")
        self.assertEqual(disk.read("/boot/kernel.bin"), b"kernel")
        self.assertEqual(disk.capacity, 64)
        self.assertEqual(disk.manifest()["/boot/kernel.bin"]["size"], 6)

    def test_path_containment_and_logical_quota(self):
        disk = VirtualStorage(8)
        with self.assertRaisesRegex(ValueError, "VSTORAGE_PATH_TRAVERSAL"):
            disk.write("/boot/../../etc/passwd", b"no")
        disk.write("/a", b"123456")
        with self.assertRaisesRegex(RuntimeError, "VSTORAGE_FULL"):
            disk.write("/b", b"123456789")
        self.assertEqual(disk.read("/a"), b"123456")

    def test_queue_depth_and_estimated_latency_are_deterministic(self):
        disk = VirtualStorage(profile_id="samsung-990-pro-1tb", queue_depth=2)
        one = disk.begin_io("read", 4096)
        two = disk.begin_io("write", 8192)
        with self.assertRaisesRegex(RuntimeError, "VSTORAGE_QUEUE_FULL"):
            disk.begin_io("read", 4096)
        self.assertGreater(two["estimated_latency_us"], 0)
        self.assertEqual(one["estimated_latency_us"], disk.estimate_latency_us("read", 4096, 1))
        disk.complete_io(one["token"])
        disk.complete_io(two["token"])
        self.assertEqual(disk.smart_telemetry()["queue_depth_current"], 0)

    def test_write_back_flush_and_restart_recovery(self):
        disk = VirtualStorage(profile_id="samsung-870-evo-1tb")
        disk.write("/data/durable", b"keep")
        self.assertGreater(disk.dirty_bytes, 0)
        disk.flush()
        disk.write("/data/volatile", b"drop")
        report = disk.restart()
        self.assertGreater(report["unflushed_bytes_lost"], 0)
        self.assertEqual(disk.read("/data/durable"), b"keep")
        with self.assertRaises(FileNotFoundError):
            disk.read("/data/volatile")
        self.assertEqual(disk.dirty_bytes, 0)

    def test_trim_and_smart_style_endurance_estimate(self):
        disk = VirtualStorage(profile_id="samsung-870-evo-1tb")
        disk.write("/large", b"x" * 4096)
        before = disk.smart_telemetry()
        self.assertGreater(before["estimated_wear_percent"], 0)
        trimmed = disk.trim("/large")
        self.assertEqual(trimmed["bytes_released_logically"], 4096)
        self.assertFalse(trimmed["physical_nand_erasure_claim"])
        after = disk.smart_telemetry()
        self.assertEqual(after["trim_ops"], 1)
        self.assertEqual(after["host_disk_allocation_bytes"], 0)
        self.assertFalse(after["smart_protocol_implemented"])

    def test_storage_workload_benchmark_is_reproducible_and_not_physical(self):
        first = run_storage_workload_benchmark("samsung-870-evo-1tb", operations=8)
        second = run_storage_workload_benchmark("samsung-870-evo-1tb", operations=8)
        self.assertEqual(first, second)
        self.assertEqual(first["total_bytes"], 8 * 4096)
        self.assertGreater(first["estimated_iops"], 0)
        self.assertIsNone(first["elapsed_host_seconds"])
        self.assertFalse(first["physical_device_measurement"])
        self.assertLessEqual(first["estimated_iops"], first["vendor_random_write_iops_qd1"])

    def test_fault_injection_is_deterministic_and_recoverable(self):
        disk = VirtualStorage(profile_id="samsung-990-pro-1tb")
        disk.write("/safe", b"persist")
        disk.flush()
        disk.write("/volatile", b"lost")
        disk.inject_fault("power_loss")
        with self.assertRaisesRegex(RuntimeError, "VSTORAGE_POWER_LOSS"):
            disk.write("/trigger", b"x")
        self.assertEqual(disk.read("/safe"), b"persist")
        with self.assertRaises(FileNotFoundError):
            disk.read("/volatile")
        disk.inject_fault("timeout")
        with self.assertRaisesRegex(TimeoutError, "VSTORAGE_INJECTED_TIMEOUT"):
            disk.read("/safe")
        self.assertEqual(disk.smart_telemetry()["host_disk_allocation_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
