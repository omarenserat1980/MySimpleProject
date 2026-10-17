from __future__ import annotations

import unittest
import hashlib
import json
from threading import RLock
from types import SimpleNamespace

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


    def _execute_federated_fixture(self, evidence_mutation=None):
        output = {"answer": 42}
        digest = hashlib.sha256(
            json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        task = SimpleNamespace(
            task_id="federated-task",
            federated_resource_id="integration-sim-01",
            lease_id="lease-test",
            physical_execution=False,
            program=[{"op": "test"}],
            status="RUNNING",
            lease_expires_at=123,
            finished_at=None,
            result=None,
        )
        released = []
        finished = []
        queue = VirtualTaskQueue.__new__(VirtualTaskQueue)
        queue.lock = RLock()
        queue.tasks = {task.task_id: task}
        queue.resources = SimpleNamespace(
            release_hybrid_resource=lambda task_id: released.append(task_id) or {"status": "RELEASED"}
        )
        queue.store = SimpleNamespace(
            finish=lambda task_id, ok, result: finished.append((task_id, ok, result))
        )
        queue.pump = lambda: None

        def executor(program, resource, context):
            evidence = {
                "task_id": context["task_id"],
                "resource_id": context["resource_id"],
                "lease_id": context["lease_id"],
                "result_sha256": digest,
            }
            if evidence_mutation:
                evidence_mutation(evidence)
            return {"ok": True, "result": output, "evidence": evidence}

        queue._execute_federated(task.task_id, {"resource_id": task.federated_resource_id}, executor)
        return task, released, finished

    def test_federated_execution_accepts_matching_receipt_and_releases_lease(self):
        task, released, finished = self._execute_federated_fixture()
        self.assertEqual(task.status, "COMPLETED")
        self.assertEqual(task.result["result"], {"answer": 42})
        self.assertEqual(released, ["federated-task"])
        self.assertEqual(len(finished), 1)
        self.assertTrue(finished[0][1])

    def test_federated_execution_rejects_mismatched_receipt_and_releases_lease(self):
        task, released, finished = self._execute_federated_fixture(
            lambda evidence: evidence.update({"resource_id": "wrong-resource"})
        )
        self.assertEqual(task.status, "FAILED")
        self.assertEqual(task.result["error"], "FEDERATED_EXECUTION_EVIDENCE_MISMATCH")
        self.assertEqual(released, ["federated-task"])
        self.assertEqual(len(finished), 1)
        self.assertFalse(finished[0][1])


if __name__ == "__main__":
    unittest.main()
