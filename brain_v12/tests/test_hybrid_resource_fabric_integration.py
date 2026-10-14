from __future__ import annotations

import unittest

from brain_v12.brain.hybrid_resource_fabric import HybridResourceFabric, RealityMode, ResourceRecord
from brain_v12.brain.resource_manager import ResourceManager
from brain_v12.brain.virtual_task_queue import VirtualTaskQueue


class HybridFabricIntegrationTests(unittest.TestCase):
    def test_register_reserve_release_through_queue_adapter(self):
        fabric = HybridResourceFabric()
        manager = ResourceManager(hybrid_fabric=fabric)
        record = ResourceRecord(
            resource_id="integration-sim-01",
            owner_id="brain",
            reality_mode=RealityMode.VIRTUAL,
            capabilities=frozenset({"cpu", "simulation"}),
            modeled_capacity={"cpu": 2},
            permissions=frozenset({"simulate"}),
        )
        manager.register_hybrid_resource(record)
        queue = VirtualTaskQueue.__new__(VirtualTaskQueue)
        queue.resources = manager

        status = queue.federated_resource_status()
        self.assertEqual(status["count"], 1)
        lease = queue.reserve_federated_resource(
            "integration-sim-01", "integration-task", {"cpu": 1}, {"cpu"}
        )
        self.assertEqual(lease["status"], "RESERVED")
        self.assertEqual(
            queue.release_federated_resource("integration-task")["status"],
            "RELEASED",
        )


if __name__ == "__main__":
    unittest.main()
