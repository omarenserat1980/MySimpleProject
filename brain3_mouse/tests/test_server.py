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
            self.assertEqual(task["state"], "SIMULATED_QUEUED")
            self.assertIs(task["emulated"], True)
            self.assertIs(task["executed"], False)
            self.assertIs(task["remote_calls"], False)
            self.assertIs(task["render"], False)
            self.assertIs(task["physical_devices"], False)
            self.assertIs(task["windows_boot_verified"], False)

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

    def test_non_loopback_bind_is_refused(self):
        with patch.dict(os.environ, {"MOUSE_HOST": "0.0.0.0"}):
            with self.assertRaisesRegex(SystemExit, "non-loopback"):
                main()


if __name__ == "__main__":
    unittest.main()
