"""Focused tests for the local-first Home Server queue."""
import sys
import tempfile
import unittest
from pathlib import Path

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

    def test_main_app_registers_home_server_routes(self):
        # Import the same app object used by Render's uvicorn start command.
        from brain_v12.app import app as main_app
        from brain_v12.home_server import router as home_server_router

        app_module = sys.modules.get("brain_v12.app")
        router_paths = {getattr(route, "path", "") for route in home_server_router.routes}
        app_routes = list(main_app.routes)
        paths = {getattr(route, "path", "") for route in app_routes}
        diagnostic = (
            f"app_module_file={getattr(app_module, '__file__', None)!r}; "
            f"app_id={id(main_app)}; module_app_id={id(getattr(app_module, 'app', None))}; "
            f"router_id={id(home_server_router)}; app_route_count={len(app_routes)}; "
            f"home_paths_in_app={[getattr(route, 'path', None) for route in app_routes if 'home-server' in getattr(route, 'path', '')]}; "
            f"router_paths={sorted(router_paths)}"
        )
        self.assertIsNotNone(app_module, diagnostic)
        self.assertIs(main_app, getattr(app_module, "app", None), diagnostic)
        self.assertIn("/api/home-server/status", router_paths, diagnostic)
        self.assertIn("/api/home-server/status", paths, diagnostic)
        self.assertIn("/api/home-server/tasks", paths, diagnostic)
        self.assertIn("/api/home-server/claim", paths, diagnostic)
        self.assertIn("/api/home-server/tasks/{task_id}/report", paths, diagnostic)

    def test_priority_range_is_validated(self):
        with self.assertRaises(ValueError):
            self.store.enqueue("status", {}, None, priority=11)


if __name__ == "__main__":
    unittest.main()
