from __future__ import annotations

import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from brain3_mouse.server import MouseHandler, STATE, main
from brain3_mouse.unified_kernel import KERNEL
from brain3_mouse.runtime_adapters import manager_for


def request(server, method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


class MouseEmulatorTests(unittest.TestCase):
    def setUp(self):
        STATE.reset()
        KERNEL.reset()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), MouseHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_health_is_explicitly_non_real(self):
        status, payload = request(self.server, "GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["name"], "Mouse")
        self.assertIs(payload["real_github"], False)
        self.assertIs(payload["render"], False)
        self.assertIs(payload["external_network"], False)
        self.assertIs(payload["physical_devices"], False)
        self.assertIs(payload["windows_boot_verified"], False)
        self.assertEqual(payload["persistence"], "memory-only")

    def test_integration_status_is_truthful_before_initialization(self):
        status, payload = request(self.server, "GET", "/api/brain3/integration")
        self.assertEqual(status, 200)
        self.assertEqual(payload["runtimes"]["initialized"], [])
        self.assertIs(payload["runtimes"]["external_side_effects"], False)
        self.assertFalse(payload["kernel"]["legacy_brain_integrated"])
        self.assertFalse(payload["kernel"]["brain_v12_integrated"])

    def test_dispatch_requires_explicit_runtime_initialization(self):
        status, payload = request(
            self.server, "POST", "/api/brain3/tasks/1/dispatch",
            {"adapter": "brain_v12", "description": "safe inspect"},
        )
        self.assertEqual(status, 503)
        self.assertIs(payload["executed"], False)

    def test_legacy_and_v12_compatibility_contract(self):
        status, payload = request(self.server, "GET", "/api/brain/compatibility")
        self.assertEqual(status, 200)
        self.assertEqual(payload["legacy_brain"]["execution"], False)
        self.assertEqual(payload["brain_v12"]["execution"], False)
        self.assertIs(payload["render"], False)
        self.assertIs(payload["physical_devices"], False)

    def test_old_and_new_brain_can_submit_simulated_non_execution_tasks(self):
        for source in ("legacy_brain", "brain_v12"):
            status, task = request(
                self.server, "POST", "/api/brain/tasks",
                {"source": source, "action": "inspect", "description": "inspect in sandbox"},
            )
            self.assertEqual(status, 202)
            self.assertEqual(task["source"], source)
            self.assertEqual(task["state"], "QUEUED")
            self.assertEqual(task["queue"], "brain3_shared")
            self.assertIs(task["emulated"], True)
            self.assertIs(task["executed"], False)
            self.assertIs(task["remote_calls"], False)
            self.assertIs(task["render"], False)
            self.assertIs(task["physical_devices"], False)
            self.assertIs(task["windows_boot_verified"], False)
        status, tasks = request(self.server, "GET", "/api/brain/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(len(tasks), 2)
        self.assertEqual({item["queue"] for item in tasks}, {"brain3_shared"})

    def test_unified_kernel_health_does_not_claim_runtime_integration(self):
        status, health = request(self.server, "GET", "/api/brain3/kernel")
        self.assertEqual(status, 200)
        self.assertTrue(health["shared_memory"])
        self.assertTrue(health["shared_task_queue"])
        self.assertFalse(health["legacy_brain_integrated"])
        self.assertFalse(health["brain_v12_integrated"])
        self.assertFalse(health["production_ready"])

    def test_real_execution_deploy_and_boot_are_blocked(self):
        for action in ("execute", "deploy", "render", "windows_boot", "device_setup", "publish"):
            status, payload = request(
                self.server, "POST", "/api/brain/tasks",
                {"source": "brain_v12", "action": action, "description": "must be blocked"},
            )
            self.assertEqual(status, 403)
            self.assertIs(payload["executed"], False)

    def test_bad_source_or_action_is_rejected(self):
        status, _ = request(
            self.server, "POST", "/api/brain/tasks",
            {"source": "unknown", "action": "inspect", "description": "bad source"},
        )
        self.assertEqual(status, 400)
        status, _ = request(
            self.server, "POST", "/api/brain/tasks",
            {"source": "brain_v12", "action": "unknown", "description": "bad action"},
        )
        self.assertEqual(status, 400)

    def test_create_local_repo_and_issue(self):
        status, repo = request(
            self.server, "POST", "/api/repos",
            {"owner": "brain3", "name": "demo"},
        )
        self.assertEqual(status, 201)
        self.assertIs(repo["emulated"], True)

        status, issue = request(
            self.server, "POST", "/api/repos/brain3/demo/issues",
            {"title": "Test Mouse"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(issue["title"], "Test Mouse")
        self.assertTrue(issue["html_url"].startswith("mouse://"))

        status, issues = request(self.server, "GET", "/api/repos/brain3/demo/issues")
        self.assertEqual(status, 200)
        self.assertEqual(len(issues), 1)

    def test_missing_repo_and_empty_issue_are_rejected(self):
        status, _ = request(
            self.server, "POST", "/api/repos/brain3/missing/issues",
            {"title": "Not created"},
        )
        self.assertEqual(status, 404)
        request(self.server, "POST", "/api/repos", {"owner": "brain3", "name": "demo"})
        status, _ = request(self.server, "POST", "/api/repos/brain3/demo/issues", {"title": ""})
        self.assertEqual(status, 400)

    def test_z_actual_runtime_adapters_and_cross_runtime_memory_bridge(self):
        manager = manager_for(KERNEL)
        runtime_status = manager.initialize()
        health = KERNEL.health()
        self.assertTrue(health["legacy_brain_integrated"], runtime_status)
        self.assertTrue(health["brain_v12_integrated"], runtime_status)

        # Seed a legacy-shaped memory record and prove the real V12 store can see it.
        KERNEL.memory_set("shared:legacy:integration_probe", {
            "key": "integration_probe", "concept": "legacy-to-v12",
            "belief": 0.7, "confidence": 0.6, "observations": 2,
            "successes": 1, "failures": 0, "last_updated": 0.0,
        })
        v12_task = KERNEL.submit("inspect", "cross-runtime memory check", "brain_v12")
        KERNEL.dispatch(v12_task["id"], "brain_v12", {"description": "cross-runtime memory check"})
        v12_store = manager._instances["brain_v12"]["store"]
        v12_keys = {item["key"] for item in v12_store.memories()}
        self.assertIn("brain3:shared:legacy:integration_probe", v12_keys)

        # And prove the real legacy memory receives V12 entries on its next boundary.
        KERNEL.memory_set("shared:v12:integration_probe", "v12-to-legacy")
        legacy_task = KERNEL.submit("inspect", "cross-runtime memory check", "legacy_brain")
        KERNEL.dispatch(legacy_task["id"], "legacy_brain", {"description": "cross-runtime memory check"})
        legacy_memory = manager._instances["legacy_brain"]["brain"].memory
        self.assertIn("v12:integration_probe", legacy_memory)

        # Verify both actual runtime handlers can perform a safe plan operation.
        v12_plan = KERNEL.submit("plan", "make a bounded local verification plan", "brain_v12")
        v12_result = KERNEL.dispatch(v12_plan["id"], "brain_v12", {
            "description": "make a bounded local verification plan",
        })
        self.assertEqual(v12_result["state"], "COMPLETED")
        self.assertTrue(v12_result["executed"])
        self.assertEqual(v12_result["result"]["status"], "PLANNED")

        legacy_plan = KERNEL.submit("plan", "analyze the safe integration plan", "legacy_brain")
        legacy_result = KERNEL.dispatch(legacy_plan["id"], "legacy_brain", {
            "description": "analyze the safe integration plan",
        })
        self.assertEqual(legacy_result["state"], "COMPLETED")
        self.assertTrue(legacy_result["executed"])
        self.assertEqual(legacy_result["result"]["runtime"], "legacy_brain")

    def test_non_loopback_bind_is_refused(self):
        with patch.dict(os.environ, {"MOUSE_HOST": "0.0.0.0"}):
            with self.assertRaisesRegex(SystemExit, "non-loopback"):
                main()


if __name__ == "__main__":
    unittest.main()
