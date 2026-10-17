import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain.device_cloud_federation import eligible_fabric_resources
from brain_v12.brain.hybrid_resource_fabric import RealityMode, ResourceRecord
from brain_v12.brain.virtual_datacenter import BrainVirtualDatacenter


class FabricPlanningTests(unittest.TestCase):
    def test_virtual_record_requires_simulation_claim(self):
        record = {
            "resource_id": "virtual-plan-01",
            "reality_mode": "VIRTUAL",
            "capabilities": ["cpu"],
        }
        result = eligible_fabric_resources({"resources": [record]}, {"cpu"})
        self.assertEqual(result["status"], "NO_ELIGIBLE_RESOURCE")
        self.assertEqual(result["eligible"], [])

    def test_virtual_simulation_record_is_plannable(self):
        record = {
            "resource_id": "virtual-plan-02",
            "reality_mode": "VIRTUAL",
            "capabilities": ["cpu", "simulation"],
            "execution_claim": "SIMULATION_ONLY",
        }
        result = eligible_fabric_resources({"resources": [record]}, {"cpu"})
        self.assertEqual(result["status"], "ELIGIBLE")
        self.assertEqual(result["eligible"], [record])

    def test_capability_filter_rejects_mismatch(self):
        record = {
            "resource_id": "virtual-plan-03",
            "reality_mode": "VIRTUAL",
            "capabilities": ["cpu"],
            "execution_claim": "SIMULATION_ONLY",
        }
        result = eligible_fabric_resources({"resources": [record]}, {"gpu"})
        self.assertEqual(result["status"], "NO_ELIGIBLE_RESOURCE")
        self.assertIn("CAPABILITY_MISMATCH", result["rejected"][0]["reasons"])


    def test_datacenter_plans_and_reserves_registered_simulation_resource(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ,
            {"BRAIN_VIRTUAL_TASK_DB": str(Path(tmpdir) / "tasks.db")},
        ):
            datacenter = BrainVirtualDatacenter(name="fabric-integration-test")
            try:
                registered = datacenter.resource_manager.register_hybrid_resource(
                    ResourceRecord(
                        resource_id="datacenter-sim-01",
                        owner_id="test-suite",
                        reality_mode=RealityMode.VIRTUAL,
                        capabilities=frozenset({"cpu", "simulation"}),
                        modeled_capacity={"cpu": 2},
                        permissions=frozenset({"simulate"}),
                    )
                )
                self.assertTrue(registered["ok"])

                plan = datacenter.plan_fabric_resources({"cpu"})
                self.assertEqual(plan["status"], "ELIGIBLE")
                self.assertEqual(
                    [item["resource_id"] for item in plan["eligible"]],
                    ["datacenter-sim-01"],
                )

                physical_plan = datacenter.plan_fabric_resources(
                    {"cpu"}, physical_execution=True
                )
                self.assertEqual(physical_plan["status"], "NO_ELIGIBLE_RESOURCE")

                lease = datacenter.reserve_hybrid_resource(
                    "datacenter-sim-01",
                    "datacenter-test-task",
                    required_capacity={"cpu": 1},
                    required_capabilities={"cpu"},
                    permission="simulate",
                )
                self.assertEqual(lease["status"], "RESERVED")
                released = datacenter.release_hybrid_resource("datacenter-test-task")
                self.assertEqual(released["status"], "RELEASED")
            finally:
                datacenter.task_queue.shutdown()


if __name__ == "__main__":
    unittest.main()
