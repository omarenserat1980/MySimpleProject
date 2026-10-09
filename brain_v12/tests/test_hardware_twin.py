import unittest

from brain_v12.virtual_hardware.hardware_twin import (
    HardwareDomain,
    HealthState,
    TruthState,
    build_complete_server_twin,
)


class HardwareTwinTests(unittest.TestCase):
    def test_complete_server_topology(self):
        twin = build_complete_server_twin(
            cpu_cores=64, memory_gb=256, storage_tb=8, network_gbps=100, gpu_count=4
        )
        self.assertGreaterEqual(len(twin.components), 16)
        self.assertGreaterEqual(len(twin.relations), 14)
        domains = {c.domain for c in twin.components.values()}
        for required in (
            HardwareDomain.CHASSIS,
            HardwareDomain.MOTHERBOARD,
            HardwareDomain.POWER,
            HardwareDomain.COOLING,
            HardwareDomain.BMC,
            HardwareDomain.CPU,
            HardwareDomain.MEMORY,
            HardwareDomain.PCIE,
            HardwareDomain.STORAGE,
            HardwareDomain.NETWORK,
            HardwareDomain.ACCELERATOR,
            HardwareDomain.FIRMWARE,
            HardwareDomain.SECURITY,
        ):
            self.assertIn(required, domains)

    def test_simulation_is_not_physical_truth(self):
        twin = build_complete_server_twin(cpu_cores=128, memory_gb=512)
        summary = twin.capacity_summary()
        self.assertEqual(summary["cores"]["simulated"], 128)
        self.assertEqual(summary["cores"]["verified"], 0)
        self.assertEqual(summary["gb"]["simulated"], 512)
        self.assertEqual(summary["gb"]["verified"], 0)

    def test_verified_binding_and_running_transition(self):
        twin = build_complete_server_twin()
        with self.assertRaises(RuntimeError):
            twin.bind_verified("cpu0", ["cpu-resource-1"], {"verified": False}, "host")
        twin.bind_verified(
            "cpu0",
            ["cpu-resource-1"],
            {"verified": True, "evidence_id": "ev-1"},
            "hyperv",
        )
        self.assertEqual(twin.components["cpu0"].truth, TruthState.ATTACHED)
        twin.mark_running("cpu0", "execution-1")
        self.assertEqual(twin.components["cpu0"].truth, TruthState.RUNNING)
        self.assertEqual(twin.capacity_summary()["cores"]["attached"], 32)

    def test_telemetry_and_health(self):
        twin = build_complete_server_twin()
        twin.record_sensor("cpu0", "temp", "temperature", 61.5, "C", HealthState.HEALTHY)
        twin.record_sensor("psu0", "power", "power", 420, "W", HealthState.HEALTHY)
        twin.mark_health("cpu0", HealthState.DEGRADED, "thermal headroom")
        self.assertEqual(twin.health_summary()["degraded"], 1)
        self.assertEqual(twin.components["cpu0"].sensors["temp"].value, 61.5)

    def test_topology_relations(self):
        twin = build_complete_server_twin(gpu_count=1)
        targets = {(r.source, r.relation, r.target) for r in twin.relations}
        self.assertIn(("bmc0", "manages", "board0"), targets)
        self.assertIn(("pcie0", "connects", "gpu0"), targets)
        self.assertIn(("cool0", "cools", "cpu0"), targets)


if __name__ == "__main__":
    unittest.main()
