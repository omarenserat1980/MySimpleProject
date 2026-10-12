from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.devices import VirtualGPU, VirtualNIC
from brain_v12.virtual_hardware.bus import VirtualBus
from brain_v12.virtual_hardware.computer import VirtualComputer
from brain_v12.virtual_hardware.peripheral_profiles import (
    get_gpu_profile, get_nic_profile, get_motherboard_profile,
)


class PeripheralProfileTests(unittest.TestCase):
    def test_documented_gpu_nic_and_board_profiles_have_sources_and_gaps(self):
        gpu = get_gpu_profile("nvidia-tesla-t4").describe()
        nic = get_nic_profile("intel-i225-v").describe()
        board = get_motherboard_profile("brain-pcie-gen4-x24").describe()
        self.assertEqual(gpu["vram_capacity_bytes"], 16_000_000_000)
        self.assertEqual(gpu["vram_bandwidth_bytes_per_second"], 320_000_000_000)
        self.assertEqual(gpu["tdp_watts"], 70.0)
        self.assertEqual(nic["link_speed_bits_per_second"], 2_500_000_000)
        self.assertEqual(nic["tdp_watts"], 1.95)
        self.assertEqual(board["model_status"], "synthetic motherboard topology, not a commercial board model")
        self.assertFalse(gpu["host_gpu_acceleration"])
        self.assertFalse(nic["external_network_enabled"])

    def test_gpu_vram_is_logical_and_compute_is_estimated_not_executed(self):
        gpu = VirtualGPU(profile_id="nvidia-tesla-t4", vram_capacity_bytes=16)
        transfer = gpu.transfer_to_vram(8)
        self.assertFalse(transfer["host_vram_allocated"])
        self.assertFalse(transfer["hardware_gpu_used"])
        with self.assertRaisesRegex(RuntimeError, "GPU_VRAM_CAPACITY_EXCEEDED"):
            gpu.transfer_to_vram(9)
        submitted = gpu.submit_compute(8_100_000)
        self.assertAlmostEqual(submitted["command"]["estimated_seconds"], 0.000001)
        completed = gpu.synchronize()
        self.assertEqual(completed["operations"], 8_100_000)
        self.assertFalse(completed["physical_gpu_execution"])
        self.assertIsNone(completed["elapsed_host_seconds"])

    def test_gpu_command_queue_backpressure_and_reset(self):
        gpu = VirtualGPU(profile_id="nvidia-tesla-t4", command_queue_depth=1)
        gpu.submit_compute(100)
        with self.assertRaisesRegex(RuntimeError, "GPU_COMMAND_QUEUE_FULL"):
            gpu.submit_compute(100)
        gpu.reset()
        self.assertEqual(gpu.status()["command_queue_current"], 0)

    def test_nic_mtu_backpressure_and_no_external_network(self):
        nic = VirtualNIC(profile_id="intel-i225-v", queue_depth=1)
        sent = nic.send(b"packet")
        self.assertFalse(sent["transmitted_to_host_network"])
        self.assertFalse(sent["external_network_enabled"])
        with self.assertRaisesRegex(RuntimeError, "VNIC_TX_QUEUE_FULL"):
            nic.send(b"another")
        nic.complete_tx()
        with self.assertRaisesRegex(ValueError, "VNIC_MTU_EXCEEDED"):
            nic.send(b"x" * 1501)
        with self.assertRaisesRegex(RuntimeError, "VNIC_EXTERNAL_NETWORK_ADAPTER_NOT_IMPLEMENTED"):
            VirtualNIC(profile_id="intel-i225-v", external_network_enabled=True)

    def test_virtual_bus_topology_dma_and_interrupt_routing(self):
        computer = VirtualComputer(
            "integrated-hardware", ram_size=1024, ram_profile_id="micron-ddr5-5600-x16",
            cache_enabled=True, storage_profile_id="samsung-990-pro-1tb",
            gpu_profile_id="nvidia-tesla-t4", nic_profile_id="intel-i225-v",
            motherboard_profile_id="brain-pcie-gen4-x24",
        )
        topology = computer.bus.validate_topology()
        self.assertTrue(topology["ok"], topology)
        self.assertEqual(topology["pcie_lanes_allocated"], 21)
        gpu_transfer = computer.gpu.transfer_to_vram(4096)
        self.assertTrue(gpu_transfer["dma"]["ok"])
        self.assertFalse(gpu_transfer["dma"]["host_dma_used"])
        sent = computer.nic.send(b"frame")
        self.assertTrue(sent["dma"]["ok"])
        manifest = computer.hardware_manifest()
        categories = manifest["validation"]["categories"]
        self.assertTrue({"gpu", "network", "motherboard", "bus", "memory", "storage"}.issubset(set(categories)))
        self.assertFalse(computer.status()["gpu"]["hardware_gpu_used"])
        self.assertFalse(computer.status()["network"]["physical_network_used"])

    def test_lane_conflict_is_rejected_before_boot(self):
        with self.assertRaisesRegex(RuntimeError, "BUS_PCIE_LANE_CONFLICT"):
            VirtualComputer(
                "overcommitted-board", ram_size=128, storage_profile_id="samsung-990-pro-1tb",
                gpu_profile_id="nvidia-tesla-t4", nic_profile_id="intel-i225-v",
                motherboard_profile_id="brain-pcie-gen3-x20",
            )

    def test_virtual_hotplug_reset_and_fault_isolation(self):
        bus = VirtualBus(profile_id="brain-pcie-gen4-x24")
        bus.attach("cpu", object())
        bus.attach("ram", object())
        nic = VirtualNIC(profile_id="intel-i225-v", interrupt_moderation_packets=1)
        nic.attach_bus(bus)
        bus.attach("nic", nic)
        sent = nic.send(b"one")
        self.assertTrue(sent["dma"]["ok"])
        self.assertEqual(len(bus.interrupts), 1)
        bus.inject_fault("dma_timeout")
        with self.assertRaisesRegex(TimeoutError, "BUS_DMA_INJECTED_TIMEOUT"):
            bus.dma_transfer("ram", "nic", 100)
        self.assertTrue(bus.reset_device("nic")["ok"])
        self.assertTrue(bus.detach("nic")["ok"])
        self.assertNotIn("nic", bus.device_names())


if __name__ == "__main__":
    unittest.main()
