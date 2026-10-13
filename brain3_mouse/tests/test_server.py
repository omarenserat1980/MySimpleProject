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
        self.assertEqual(payload["persistence"], "memory-only")

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
