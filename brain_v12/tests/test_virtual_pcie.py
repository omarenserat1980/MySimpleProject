from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.bus import VirtualBus
from brain_v12.virtual_hardware.pcie import VirtualPCIeBAR, VirtualPCIeEndpoint, VirtualPCIeFabric


class VirtualPCIeTests(unittest.TestCase):
    def test_endpoint_discovery_and_config_space(self):
        fabric = VirtualPCIeFabric(generation=5, lane_count=16)
        created = fabric.attach_endpoint("nic0", vendor_id=0x1234, device_id=0xABCD,
                                         class_code=0x020000, bar_sizes={0: 4096, 2: 8192})
        self.assertEqual(created["bdf"], "00:01.0")
        self.assertFalse(created["host_mmio_mapped"])
        vendor = fabric.config_read("nic0", 0, 2)
        device = fabric.config_read("nic0", 2, 2)
        self.assertEqual(vendor["value"], 0x1234)
        self.assertEqual(device["value"], 0xABCD)
        self.assertEqual(fabric.config_read("nic0", 9, 1)["value"], 0x00)
        self.assertEqual(fabric.config_read("nic0", 10, 2)["value"], 0x0200)
        self.assertEqual(fabric.status()["generation"], 5)

    def test_config_command_register_is_writable_ids_are_not(self):
        fabric = VirtualPCIeFabric()
        fabric.attach_endpoint("gpu0")
        self.assertTrue(fabric.config_write("gpu0", 4, 0x0002, 2)["ok"])
        self.assertEqual(fabric.config_read("gpu0", 4, 2)["value"], 0x0002)
        with self.assertRaisesRegex(PermissionError, "VPCIE_CONFIG_REGISTER_READ_ONLY"):
            fabric.config_write("gpu0", 0, 0, 2)

    def test_mmio_is_sparse_little_endian_and_bounds_checked(self):
        fabric = VirtualPCIeFabric()
        fabric.attach_endpoint("gpu0", bar_sizes={0: 4096})
        self.assertTrue(fabric.mmio_write("gpu0", 0, 4, 0x12345678)["ok"])
        self.assertEqual(fabric.mmio_read("gpu0", 0, 4)["value"], 0x12345678)
        self.assertEqual(fabric.mmio_read("gpu0", 0, 5, 1)["value"], 0x56)
        self.assertEqual(fabric.status()["endpoints"][0]["bars"][0]["host_mapping"], False)
        with self.assertRaisesRegex(ValueError, "VPCIE_MMIO_ALIGNMENT_INVALID"):
            fabric.mmio_read("gpu0", 0, 3, 4)
        with self.assertRaisesRegex(ValueError, "VPCIE_MMIO_OUT_OF_BAR_RANGE"):
            fabric.mmio_read("gpu0", 0, 4096, 4)

    def test_transport_faults_do_not_apply_failed_mmio_write(self):
        fabric = VirtualPCIeFabric()
        fabric.attach_endpoint("nic0")
        fabric.inject_fault("completion_timeout")
        failed = fabric.mmio_write("nic0", 0, 0, 0xCAFE)
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["status"], "COMPLETION_TIMEOUT")
        self.assertEqual(fabric.mmio_read("nic0", 0, 0)["value"], 0)
        fabric.inject_fault("drop_transaction")
        dropped = fabric.mmio_read("nic0", 0, 0)
        self.assertFalse(dropped["ok"])
        self.assertEqual(dropped["status"], "TRANSACTION_DROPPED")
        self.assertEqual(fabric.status()["stats"]["timeouts"], 1)
        self.assertEqual(fabric.status()["stats"]["dropped"], 1)

    def test_transaction_trace_is_bounded_and_faults_are_validated(self):
        fabric = VirtualPCIeFabric(trace_limit=3)
        fabric.attach_endpoint("disk0")
        for i in range(6):
            fabric.mmio_write("disk0", 0, 4 * i, i)
        self.assertEqual(len(fabric.transactions), 3)
        self.assertEqual(fabric.transactions[0]["sequence"], 4)
        with self.assertRaisesRegex(ValueError, "VPCIE_FAULT_UNSUPPORTED"):
            fabric.inject_fault("host_access")

    def test_bus_exposes_pcie_for_peripherals_and_detaches_endpoint(self):
        bus = VirtualBus()
        bus.attach("cpu", object())
        bus.attach("gpu", object())
        self.assertEqual(bus.config_read("gpu", 0, 2)["value"], 0xB12A)
        bus.mmio_write("gpu", 0, 0, 42)
        self.assertEqual(bus.mmio_read("gpu", 0, 0)["value"], 42)
        self.assertIn("pcie", bus.status())
        self.assertTrue(bus.detach("gpu")["ok"])
        with self.assertRaisesRegex(KeyError, "VPCIE_ENDPOINT_NOT_FOUND"):
            bus.mmio_read("gpu", 0, 0)

    def test_invalid_bar_and_bdf_rejected(self):
        with self.assertRaisesRegex(ValueError, "VPCIE_BAR_SIZE_INVALID"):
            VirtualPCIeBAR(0, 3000)
        with self.assertRaisesRegex(ValueError, "VPCIE_BDF_INVALID"):
            VirtualPCIeEndpoint("bad", 0, 32)


if __name__ == "__main__":
    unittest.main()
