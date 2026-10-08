import unittest

from brain_v12.virtual_hardware.machine import (
    DeviceState,
    MachineState,
    VirtualHardwareMachine,
    VirtualDeviceSpec,
    build_brain_server,
)


class VirtualHardwareMachineTests(unittest.TestCase):
    def test_builds_complete_virtual_server(self):
        m = build_brain_server(vcpu=32, memory_gb=64, storage_gb=1024, gpu=True)
        self.assertEqual(m.status()["device_count"], 6)
        self.assertEqual(m.status()["capacity_truth"], "VIRTUAL_UNTIL_VERIFIED")
        self.assertEqual(m.devices["cpu0"].capacity["cores"], 32)

    def test_topology_mmio_and_irq_are_exclusive(self):
        m = VirtualHardwareMachine("test")
        m.add_device(VirtualDeviceSpec("nic0", "VNIC", "pci:0"))
        m.add_device(VirtualDeviceSpec("disk0", "VNVME", "storage:0"))
        m.map_mmio("nic0", 0x1000, 0x100)
        m.route_irq(11, "nic0")
        with self.assertRaises(ValueError):
            m.map_mmio("disk0", 0x1080, 0x100)
        with self.assertRaises(ValueError):
            m.route_irq(11, "disk0")

    def test_physical_binding_requires_verified_evidence(self):
        m = build_brain_server()
        with self.assertRaises(RuntimeError):
            m.bind_physical("cpu0", "arkan", ["cpu:0"], {"verified": False})
        result = m.bind_physical(
            "cpu0",
            "arkan",
            ["cpu:0"],
            {"verified": True, "source": "resource_fabric", "evidence_id": "ev-1"},
        )
        self.assertEqual(result["provider_id"], "arkan")
        self.assertEqual(m.device_state["cpu0"], DeviceState.ATTACHED)

    def test_machine_cannot_claim_power_without_capacity_verification(self):
        m = build_brain_server()
        with self.assertRaises(RuntimeError):
            m.start()
        self.assertEqual(m.state, MachineState.CREATED)
        m.start(physical_capacity_verified=True)
        self.assertEqual(m.state, MachineState.RUNNING)
        m.pause()
        self.assertEqual(m.state, MachineState.PAUSED)
        m.resume()
        m.stop()
        self.assertEqual(m.state, MachineState.STOPPED)


if __name__ == "__main__":
    unittest.main()
