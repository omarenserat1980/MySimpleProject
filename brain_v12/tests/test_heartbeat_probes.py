"""Tests for the ten bounded read-only local heartbeat probes."""
from __future__ import annotations

import sqlite3
import unittest

from brain_v12.brain.heartbeat_factory import HeartbeatFactory
from brain_v12.brain.heartbeat_probes import register_core_probes, run_core_probes, run_local_probe


class FakeStore:
    def state(self):
        return {"status": "READY"}


class FakeCognitive:
    STAGES = ("PERCEIVE", "DECIDE", "ACT")


class FakeQueue:
    def counts(self):
        return {"PENDING": 1, "FAILED": 0, "ACKED": 2}


class FakeSyncStore:
    def snapshot(self):
        return {"digest": "a" * 64, "audit_chain_valid": True}


class FakeWorkerRegistry:
    def snapshot(self):
        return {"ok": True, "mode": "software-only", "workers": [], "device_adapters_enabled": False}


class FakeSelfMonitor:
    def snapshot(self):
        return {"ok": True, "status": "HEALTHY", "checks": [{"name": "repo", "ok": True}]}


class FakeEvidenceStore:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row


class FakeDeviceBridge:
    def status(self):
        return {"configured": False, "agents": {"online": False}, "queued": 0, "pending": 0}


class FakeRoute:
    def __init__(self, path):
        self.path = path


class FakeApp:
    routes = [
        FakeRoute("/api/system/readiness"),
        FakeRoute("/api/heartbeats/summary"),
        FakeRoute("/api/heartbeats/diagnostic"),
    ]


class HeartbeatProbeTests(unittest.TestCase):
    def setUp(self):
        self.factory = HeartbeatFactory(":memory:")
        self.addCleanup(self.factory.close)
        self.context = {
            "store": FakeStore(),
            "cognitive": FakeCognitive(),
            "sync_queue": FakeQueue(),
            "sync_store": FakeSyncStore(),
            "worker_registry": FakeWorkerRegistry(),
            "self_monitor": FakeSelfMonitor(),
            "evidence_store": FakeEvidenceStore(),
            "device_bridge": FakeDeviceBridge(),
            "app": FakeApp(),
        }
        self.addCleanup(self.context["evidence_store"].db.close)
        register_core_probes(self.factory, now=100.0)

    def test_ten_concrete_local_probes_are_registered_idempotently(self):
        first = register_core_probes(self.factory, now=101.0)
        second = register_core_probes(self.factory, now=102.0)
        self.assertEqual(len(first), 10)
        self.assertEqual(len(second), 10)
        self.assertEqual(len(self.factory.list_functions()), 10)
        self.assertEqual(self.factory.summary()["functions_enabled"], 10)
        self.assertTrue(all(item["implementation"] == "local_read_only_probe" for item in second))

    def test_core_probe_batch_runs_without_network_and_does_not_claim_remote_delivery(self):
        result = run_core_probes(
            self.factory, self.context, authorization_ref="test-authorized-caller", now=103.0
        )
        self.assertEqual(result["count"], 10)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["unknown"], 1)  # Optional, unconfigured device bridge.
        self.assertEqual(result["passed"], 9)
        self.assertFalse(result["scheduler_running"])
        self.assertFalse(result["remote_delivery_proven"])
        self.assertTrue(all(item["delivery_status"] == "CREATED" for item in result["results"]))
        self.assertTrue(all(item["remote_delivery_proven"] is False for item in result["results"]))
        self.assertEqual(self.factory.summary()["heartbeats_total"], 10)
        for function in self.factory.list_functions():
            self.assertEqual(function["last_execution_status"], "PASS" if function["function_id"] != "brain.device_bridge" else "UNKNOWN")
            self.assertEqual(function["last_execution_at"], 103.0)
        self.assertEqual(self.factory.delayed_functions(now=150.0), [])
        self.assertEqual(len(self.factory.delayed_functions(now=164.0)), 10)

    def test_probe_is_not_run_without_authorization_reference(self):
        with self.assertRaisesRegex(PermissionError, "AUTHORIZATION_REFERENCE_REQUIRED"):
            run_local_probe(self.factory, "brain.python_runtime", self.context, now=103.0)
        self.assertEqual(self.factory.summary()["heartbeats_total"], 0)

    def test_unknown_probe_id_fails_closed(self):
        with self.assertRaisesRegex(KeyError, "LOCAL_PROBE_NOT_IMPLEMENTED"):
            run_local_probe(self.factory, "brain.fake_remote_probe", self.context,
                            authorization_ref="test-authorized-caller", now=103.0)

    def test_batch_limit_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "LOCAL_PROBE_BATCH_LIMIT_EXCEEDED"):
            run_core_probes(self.factory, self.context, function_ids=["brain.python_runtime"] * 11,
                            authorization_ref="test-authorized-caller", now=103.0)

    def test_probe_exception_is_classified_without_persisting_exception_text(self):
        self.context["self_monitor"] = type("BrokenMonitor", (), {
            "snapshot": lambda _self: (_ for _ in ()).throw(RuntimeError("private-path-and-secret"))
        })()
        result = run_local_probe(
            self.factory, "brain.self_monitor", self.context,
            authorization_ref="test-authorized-caller", now=103.0,
        )
        self.assertEqual(result["probe_status"], "FAIL")
        heartbeat = self.factory.get_heartbeat(result["heartbeat_id"])
        self.assertNotIn("private-path-and-secret", str(heartbeat["payload"]))


if __name__ == "__main__":
    unittest.main()
