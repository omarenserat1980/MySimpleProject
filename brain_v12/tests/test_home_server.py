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

    def test_report_rejects_expired_lease(self):
        created = self.store.enqueue("status", {}, None)
        self.store.claim("worker-a", 60)
        with self.store.connect() as db:
            db.execute("UPDATE home_tasks SET lease_until=0 WHERE task_id=?", (created["task_id"],))
        with self.assertRaisesRegex(PermissionError, "WORKER_LEASE_EXPIRED"):
            self.store.report(created["task_id"], "worker-a", True, {"status": "late"}, "")

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


class HomeServerAgentRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        agent_path = Path(__file__).resolve().parents[2] / "v12-agent" / "home_server_agent.py"
        spec = importlib.util.spec_from_file_location("brain_home_server_agent", agent_path)
        cls.agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.agent)

    def test_agent_executes_allowlisted_python_version(self):
        result = self.agent.execute_task("python_version")
        self.assertTrue(result["python"])
        self.assertTrue(result["executable"])

    def test_agent_rejects_arbitrary_commands(self):
        with self.assertRaisesRegex(ValueError, "TASK_NOT_ALLOWED"):
            self.agent.execute_task("shell", {"command": "whoami"})

    def test_agent_claim_execute_report_round_trip(self):
        responses = [
            {"ok": True, "status": "TASK_AVAILABLE", "task": {
                "task_id": "home-test-1", "task": "python_version", "params": {}
            }},
            {"ok": True, "task": {"task_id": "home-test-1", "status": "COMPLETED"}},
        ]
        calls = []

        def fake_request(method, path, key, payload=None):
            calls.append((method, path, payload))
            return responses.pop(0)

        with patch.object(self.agent, "request_json", side_effect=fake_request):
            result = self.agent.run_once("test-key")

        self.assertTrue(result["ok"])
        self.assertEqual(result["task_id"], "home-test-1")
        self.assertEqual(result["reported_status"], "COMPLETED")
        self.assertEqual(calls[0][1], "/api/home-server/claim")
        self.assertEqual(calls[1][1], "/api/home-server/tasks/home-test-1/report")
        self.assertTrue(calls[1][2]["ok"])
        self.assertIn("python", calls[1][2]["result"])


    def test_status_requires_control_auth_and_hides_database_path(self):
        previous_store = home_server.store
        home_server.store = self.store
        try:
            with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": "control-test-key"}, clear=True):
                client = TestClient(home_server.app)
                denied = client.get("/api/home-server/status")
                self.assertEqual(denied.status_code, 401)

                allowed = client.get(
                    "/api/home-server/status",
                    headers={"Authorization": "Bearer control-test-key"},
                )
                self.assertEqual(allowed.status_code, 200, allowed.text)
                payload = allowed.json()
                self.assertTrue(payload["ok"])
                self.assertNotIn("database_path", payload)
                self.assertTrue(payload["control_auth_configured"])

            with patch.dict(os.environ, {}, clear=True):
                unconfigured = client.get("/api/home-server/status")
                self.assertEqual(unconfigured.status_code, 503)
                self.assertEqual(
                    unconfigured.json()["detail"],
                    "HOME_SERVER_CONTROL_NOT_CONFIGURED",
                )
        finally:
            home_server.store = previous_store


if __name__ == "__main__":
    unittest.main()
