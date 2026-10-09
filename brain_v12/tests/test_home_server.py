"""Focused tests for the local-first Home Server queue and HTTP task round-trip."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import brain_v12.home_server as home_server
from brain_v12.home_server import HomeServerStore


class HomeServerQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = HomeServerStore(Path(self.temp.name) / "home.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_enqueue_is_idempotent(self):
        first = self.store.enqueue("python_version", {}, "request-1")
        second = self.store.enqueue("python_version", {"ignored": True}, "request-1")
        self.assertEqual(first["task_id"], second["task_id"])
        self.assertEqual(self.store.status()["queue"]["QUEUED"], 1)

    def test_claim_and_report_require_same_worker(self):
        created = self.store.enqueue("platform", {}, None)
        claim = self.store.claim("worker-a", 60)
        self.assertEqual(claim["task"]["task_id"], created["task_id"])
        with self.assertRaises(PermissionError):
            self.store.report(created["task_id"], "worker-b", True, {"system": "test"}, "")
        report = self.store.report(created["task_id"], "worker-a", True, {"system": "test"}, "")
        self.assertEqual(report["task"]["status"], "COMPLETED")
        self.assertEqual(self.store.status()["queue"]["COMPLETED"], 1)

    def test_http_control_to_worker_round_trip(self):
        previous_store = home_server.store
        home_server.store = self.store
        try:
            with patch.dict(os.environ, {
                "BRAIN_CONTROL_KEY": "control-test-key",
                "BRAIN_AGENT_KEY": "worker-test-key",
            }, clear=True):
                client = TestClient(home_server.app)
                created_response = client.post(
                    "/api/home-server/tasks",
                    headers={"Authorization": "Bearer control-test-key"},
                    json={"task": "python_version", "params": {}, "idempotency_key": "http-round-trip-1"},
                )
                self.assertEqual(created_response.status_code, 200, created_response.text)
                task_id = created_response.json()["task"]["task_id"]

                # Control credentials must not be accepted for worker claim operations.
                denied_claim = client.post(
                    "/api/home-server/claim",
                    headers={"Authorization": "Bearer control-test-key"},
                    json={"worker_id": "worker-test", "lease_seconds": 60},
                )
                self.assertEqual(denied_claim.status_code, 401)

                claimed_response = client.post(
                    "/api/home-server/claim",
                    headers={"Authorization": "Bearer worker-test-key"},
                    json={"worker_id": "worker-test", "lease_seconds": 60, "capabilities": ["python"]},
                )
                self.assertEqual(claimed_response.status_code, 200, claimed_response.text)
                self.assertEqual(claimed_response.json()["task"]["task_id"], task_id)

                reported_response = client.post(
                    f"/api/home-server/tasks/{task_id}/report",
                    headers={"Authorization": "Bearer worker-test-key"},
                    json={"worker_id": "worker-test", "ok": True, "result": {"python": "test-version"}, "error": ""},
                )
                self.assertEqual(reported_response.status_code, 200, reported_response.text)
                self.assertEqual(reported_response.json()["task"]["status"], "COMPLETED")

                listed_response = client.get(
                    "/api/home-server/tasks",
                    headers={"Authorization": "Bearer control-test-key"},
                )
                self.assertEqual(listed_response.status_code, 200, listed_response.text)
                listed = listed_response.json()["tasks"]
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["result"], {"python": "test-version"})
        finally:
            home_server.store = previous_store

    def test_unknown_task_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.enqueue("arbitrary_shell", {"command": "whoami"}, None)

    def test_expired_lease_is_requeued(self):
        created = self.store.enqueue("status", {}, None)
        self.store.claim("worker-a", 10)
        with self.store.connect() as db:
            db.execute("UPDATE home_tasks SET lease_until=0 WHERE task_id=?", (created["task_id"],))
        next_claim = self.store.claim("worker-b", 30)
        self.assertEqual(next_claim["task"]["task_id"], created["task_id"])
        self.assertEqual(next_claim["task"]["attempts"], 2)

    def test_scheduler_prefers_higher_priority(self):
        low = self.store.enqueue("status", {}, None, priority=0)
        high = self.store.enqueue("python_version", {}, None, priority=8)
        claim = self.store.claim("worker-a", 60)
        self.assertEqual(claim["task"]["task_id"], high["task_id"])
        self.assertNotEqual(claim["task"]["task_id"], low["task_id"])

    def test_scheduler_only_assigns_supported_capabilities(self):
        gpu_task = self.store.enqueue("brain_self_test", {}, None, required_capabilities=["gpu"])
        claim = self.store.claim("worker-cpu", 60, capabilities=["python"])
        self.assertEqual(claim["status"], "IDLE")
        claim = self.store.claim("worker-gpu", 60, capabilities=["python", "gpu"])
        self.assertEqual(claim["task"]["task_id"], gpu_task["task_id"])

    def test_priority_range_is_validated(self):
        with self.assertRaises(ValueError):
            self.store.enqueue("status", {}, None, priority=11)


if __name__ == "__main__":
    unittest.main()
