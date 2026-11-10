from __future__ import annotations

import unittest

from brain_v12.brain.resource_manager import ResourceManager
from brain_v12.brain.virtual_task_queue import VirtualTaskQueue
from brain_v12.brain.device_cloud_federation import eligible_fabric_resources
from brain_v12.brain.hybrid_resource_fabric import (
    FabricError,
    HybridResourceFabric,
    RealityMode,
    ResourceEvidence,
    ResourceRecord,
)


class HybridResourceFabricTests(unittest.TestCase):
    def setUp(self):
        self.now = 1_800_000_000.0
        self.fabric = HybridResourceFabric(evidence_ttl_seconds=30, clock=lambda: self.now, trusted_evidence_sources={"authenticated-agent"})

    def virtual(self, resource_id="sim-01", capacity=None):
        return ResourceRecord(
            resource_id=resource_id,
            owner_id="brain",
            reality_mode=RealityMode.VIRTUAL,
            capabilities=frozenset({"cpu", "simulation"}),
            modeled_capacity=capacity or {"cpu": 4, "ram_bytes": 4096},
            permissions=frozenset({"simulate"}),
        )

    def physical(self, resource_id="host-01", evidence_at=None, verified=True):
        return ResourceRecord(
            resource_id=resource_id,
            owner_id="operator",
            reality_mode=RealityMode.PHYSICAL,
            capabilities=frozenset({"cpu", "build"}),
            measured_host_capacity={"cpu": 8, "ram_bytes": 8192},
            evidence=ResourceEvidence("authenticated-agent", "proof-001", self.now if evidence_at is None else evidence_at, verified),
            permissions=frozenset({"simulate", "execute_physical"}),
        )

    def test_virtual_capacity_is_never_physical_eligibility(self):
        self.fabric.register(self.virtual())
        view = self.fabric.get("sim-01")["resource"]
        self.assertEqual(view["execution_claim"], "SIMULATION_ONLY")
        self.assertFalse(view["eligible_for_physical_work"])
        result = self.fabric.reserve("sim-01", "task-physical", {"cpu": 1}, {"cpu"}, "execute_physical", physical_execution=True)
        self.assertEqual(result["status"], "PHYSICAL_EVIDENCE_GATE_BLOCKED")

    def test_physical_work_requires_fresh_verified_evidence(self):
        self.fabric.register(self.physical(verified=False))
        result = self.fabric.reserve("host-01", "task-1", {"cpu": 1}, {"cpu"}, "execute_physical", physical_execution=True)
        self.assertEqual(result["status"], "PHYSICAL_EVIDENCE_GATE_BLOCKED")
        self.fabric.register(self.physical(evidence_at=self.now - 100))
        result = self.fabric.reserve("host-01", "task-2", {"cpu": 1}, {"cpu"}, "execute_physical", physical_execution=True)
        self.assertEqual(result["status"], "PHYSICAL_EVIDENCE_GATE_BLOCKED")

    def test_untrusted_evidence_source_is_blocked(self):
        untrusted = ResourceRecord(
            resource_id="host-untrusted",
            owner_id="operator",
            reality_mode=RealityMode.PHYSICAL,
            capabilities=frozenset({"cpu"}),
            measured_host_capacity={"cpu": 8},
            evidence=ResourceEvidence("untrusted-agent", "proof-x", self.now, True),
            permissions=frozenset({"simulate", "execute_physical"}),
        )
        self.fabric.register(untrusted)
        result = self.fabric.reserve("host-untrusted", "task-untrusted", {"cpu": 1}, {"cpu"}, "execute_physical", physical_execution=True)
        self.assertEqual(result["status"], "PHYSICAL_EVIDENCE_GATE_BLOCKED")

    def test_verified_physical_capacity_can_be_leased(self):
        self.fabric.register(self.physical())
        result = self.fabric.reserve("host-01", "task-1", {"cpu": 2}, {"cpu"}, "execute_physical", physical_execution=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "RESERVED")
        self.assertTrue(result["lease"]["lease_id"].startswith("lease-"))

    def test_capacity_is_reserved_and_prevents_overcommit(self):
        self.fabric.register(self.virtual(capacity={"cpu": 2}))
        first = self.fabric.reserve("sim-01", "task-1", {"cpu": 2}, {"cpu"})
        second = self.fabric.reserve("sim-01", "task-2", {"cpu": 1}, {"cpu"})
        self.assertTrue(first["ok"])
        self.assertEqual(second["status"], "INSUFFICIENT_CAPACITY")

    def test_task_cannot_hold_two_resource_leases(self):
        self.fabric.register(self.virtual("sim-01"))
        self.fabric.register(self.virtual("sim-02"))
        self.assertTrue(self.fabric.reserve("sim-01", "same-task", {"cpu": 1}, {"cpu"})["ok"])
        result = self.fabric.reserve("sim-02", "same-task", {"cpu": 1}, {"cpu"})
        self.assertEqual(result["status"], "TASK_ALREADY_LEASED")

    def test_same_task_reservation_is_idempotent_on_same_resource(self):
        self.fabric.register(self.virtual())
        first = self.fabric.reserve("sim-01", "task-1", {"cpu": 1}, {"cpu"})
        second = self.fabric.reserve("sim-01", "task-1", {"cpu": 1}, {"cpu"})
        self.assertEqual(second["status"], "ALREADY_RESERVED")
        self.assertEqual(first["lease"]["lease_id"], second["lease"]["lease_id"])

    def test_same_task_cannot_escalate_simulation_lease_to_physical(self):
        self.fabric.register(self.physical())
        simulation = self.fabric.reserve(
            "host-01", "same-task", {"cpu": 1}, {"cpu"}, permission="simulate"
        )
        self.assertEqual(simulation["status"], "RESERVED")
        escalation = self.fabric.reserve(
            "host-01", "same-task", {"cpu": 1}, {"cpu"},
            permission="execute_physical", physical_execution=True,
        )
        self.assertEqual(escalation["status"], "LEASE_REQUEST_MISMATCH")
        self.assertFalse(simulation["lease"]["physical_execution"])
        self.assertEqual(self.fabric.get("host-01")["resource"]["active_leases"], 1)

    def test_same_task_cannot_change_capacity_on_active_lease(self):
        self.fabric.register(self.virtual(capacity={"cpu": 4}))
        self.fabric.reserve("sim-01", "same-task", {"cpu": 1}, {"cpu"})
        changed = self.fabric.reserve("sim-01", "same-task", {"cpu": 2}, {"cpu"})
        self.assertEqual(changed["status"], "LEASE_REQUEST_MISMATCH")

    def test_expired_lease_is_reclaimed(self):
        self.fabric.register(self.virtual(capacity={"cpu": 1}))
        self.assertTrue(self.fabric.reserve("sim-01", "task-1", {"cpu": 1}, {"cpu"}, lease_seconds=2)["ok"])
        self.now += 3
        self.assertTrue(self.fabric.reserve("sim-01", "task-2", {"cpu": 1}, {"cpu"})["ok"])

    def test_identity_cannot_be_reclassified(self):
        self.fabric.register(self.virtual("fixed-id"))
        with self.assertRaisesRegex(FabricError, "RESOURCE_IDENTITY_CONFLICT"):
            self.fabric.register(self.physical("fixed-id"))

    def test_permission_and_capability_gates(self):
        self.fabric.register(self.virtual())
        denied = self.fabric.reserve("sim-01", "task-1", {"cpu": 1}, {"cpu"}, "execute_physical")
        mismatch = self.fabric.reserve("sim-01", "task-2", {"cpu": 1}, {"gpu"})
        self.assertEqual(denied["status"], "PERMISSION_DENIED")
        self.assertEqual(mismatch["status"], "CAPABILITY_MISMATCH")

    def test_negative_capacity_rejected(self):
        with self.assertRaisesRegex(FabricError, "INVALID_MODELED_CAPACITY"):
            self.fabric.register(self.virtual(capacity={"cpu": -1}))

    def test_resource_manager_exposes_fabric_without_claiming_physical_capacity(self):
        manager = ResourceManager()
        manager.register_hybrid_resource(self.virtual())
        status = manager.hybrid_resource_status()
        self.assertEqual(status["count"], 1)
        self.assertEqual(status["resources"][0]["execution_claim"], "SIMULATION_ONLY")
        result = manager.reserve_hybrid_resource("sim-01", "manager-task", {"cpu": 1}, {"cpu"})
        self.assertEqual(result["status"], "RESERVED")
        self.assertEqual(manager.release_hybrid_resource("manager-task")["status"], "RELEASED")

    def test_virtual_task_queue_exposes_explicit_fabric_reservations(self):
        manager = ResourceManager()
        manager.register_hybrid_resource(self.virtual())
        queue = VirtualTaskQueue.__new__(VirtualTaskQueue)
        queue.resources = manager
        result = queue.reserve_federated_resource("sim-01", "queue-task", {"cpu": 1}, {"cpu"})
        self.assertEqual(result["status"], "RESERVED")
        self.assertEqual(queue.federated_resource_status()["count"], 1)
        self.assertEqual(queue.release_federated_resource("queue-task")["status"], "RELEASED")

    def test_release_is_idempotent(self):
        self.fabric.register(self.virtual())
        self.fabric.reserve("sim-01", "task-1", {"cpu": 1}, {"cpu"})
        self.assertEqual(self.fabric.release("task-1")["status"], "RELEASED")
        self.assertEqual(self.fabric.release("task-1")["status"], "NOT_RESERVED")


if __name__ == "__main__":
    unittest.main()
