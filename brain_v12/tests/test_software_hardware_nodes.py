from __future__ import annotations
import unittest
from brain_v12.virtual_hardware.device_catalog import DEVICE_FAMILIES, COMPONENT_CLASSES
from brain_v12.virtual_hardware.network_hardware import NETWORK_DEVICE_KINDS
from brain_v12.virtual_hardware.software_hardware_nodes import SoftwareHardwareNodeFabric

class SoftwareHardwareNodeFabricTests(unittest.TestCase):
    def test_every_family_component_pair_has_a_node(self):
        fabric = SoftwareHardwareNodeFabric()
        for family_id, family in DEVICE_FAMILIES.items():
            for component_id in family["components"]:
                node_id = f"device.{family_id}.{component_id}"
                self.assertIn(node_id, fabric.nodes)
                status = fabric.get_node(node_id)
                self.assertFalse(status["physical_hardware_required"])
                self.assertFalse(status["full_device_emulation_claimed"])

    def test_every_network_kind_has_a_node(self):
        fabric = SoftwareHardwareNodeFabric()
        for kind in NETWORK_DEVICE_KINDS:
            self.assertEqual(fabric.get_node(f"network.{kind}")["fidelity"], "logical_simulation")

    def test_inventory_is_complete_and_software_only(self):
        fabric = SoftwareHardwareNodeFabric()
        inventory = fabric.inventory()
        expected_pairs = sum(len(set(f["components"])) for f in DEVICE_FAMILIES.values())
        self.assertEqual(inventory["software_node_count"], expected_pairs + len(NETWORK_DEVICE_KINDS))
        self.assertEqual(inventory["family_count"], len(DEVICE_FAMILIES))
        self.assertEqual(inventory["component_class_count"], len(COMPONENT_CLASSES))
        self.assertFalse(inventory["physical_hardware_required"])
        self.assertFalse(inventory["external_io_enabled"])
        self.assertTrue(fabric.validate()["ok"])

    def test_node_lifecycle_and_dependencies(self):
        fabric = SoftwareHardwareNodeFabric()
        cpu = "device.desktop_pc.cpu"
        ram = "device.desktop_pc.ram"
        self.assertEqual(fabric.set_dependencies(cpu, [ram])["dependencies"], [ram])
        self.assertEqual(fabric.set_enabled(cpu, False)["state"], "DISABLED")
        self.assertEqual(fabric.set_enabled(cpu, True)["state"], "READY")
        with self.assertRaisesRegex(ValueError, "SOFTWARE_HARDWARE_DEPENDENCY_UNKNOWN"):
            fabric.set_dependencies(cpu, ["missing.node"])
        with self.assertRaisesRegex(ValueError, "SOFTWARE_HARDWARE_SELF_DEPENDENCY"):
            fabric.set_dependencies(cpu, [cpu])

if __name__ == "__main__":
    unittest.main()
