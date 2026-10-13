from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from brain3_mouse.server import MouseHandler, STATE


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


def test_mouse_health_is_explicitly_non_real():
    server = ThreadingHTTPServer(("127.0.0.1", 0), MouseHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    STATE.reset()
    thread.start()
    try:
        status, payload = request(server, "GET", "/health")
        assert status == 200
        assert payload["name"] == "Mouse"
        assert payload["real_github"] is False
        assert payload["render"] is False
        assert payload["persistence"] == "memory-only"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_mouse_can_create_local_repo_and_issue():
    server = ThreadingHTTPServer(("127.0.0.1", 0), MouseHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    STATE.reset()
    thread.start()
    try:
        status, repo = request(server, "POST", "/api/repos", {"owner": "brain3", "name": "demo"})
        assert status == 201
        assert repo["emulated"] is True

        status, issue = request(server, "POST", "/api/repos/brain3/demo/issues", {"title": "Test Mouse"})
        assert status == 201
        assert issue["title"] == "Test Mouse"
        assert issue["html_url"].startswith("mouse://")

        status, issues = request(server, "GET", "/api/repos/brain3/demo/issues")
        assert status == 200
        assert len(issues) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_mouse_does_not_accept_external_bind():
    import os
    from unittest.mock import patch
    from brain3_mouse.server import main

    with patch.dict(os.environ, {"MOUSE_HOST": "0.0.0.0"}):
        try:
            main()
        except SystemExit as exc:
            assert "non-loopback" in str(exc)
        else:
            raise AssertionError("Mouse must refuse external binding")
