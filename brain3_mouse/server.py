#!/usr/bin/env python3
"""Mouse: an offline GitHub-shaped API and Brain compatibility emulator.

This service is local-only, in-memory, and non-authoritative. It never calls
GitHub, Render, devices, shell commands, or any remote service.
"""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlparse

from .unified_kernel import KERNEL


ALLOWED_SOURCES = {"legacy_brain", "brain_v12"}
ALLOWED_ACTIONS = {"inspect", "test", "plan"}
BLOCKED_ACTIONS = {"execute", "deploy", "render", "windows_boot", "device_setup", "publish"}


class MouseState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.repositories: dict[str, dict] = {}
        self.tasks: list[dict] = []
        self.next_issue = 1
        self.next_task = 1

    def reset(self) -> None:
        with self.lock:
            self.repositories.clear()
            self.tasks.clear()
            self.next_issue = 1
            self.next_task = 1


STATE = MouseState()


class MouseHandler(BaseHTTPRequestHandler):
    server_version = "MouseGitHubEmulator/0.2"

    def log_message(self, fmt: str, *args) -> None:
        if os.getenv("MOUSE_ACCESS_LOG", "0") == "1":
            super().log_message(fmt, *args)

    def _send(self, status: int, payload: dict | list) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 65536:
                raise ValueError("request body too large")
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON body must be an object")
            return data
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid JSON request") from exc

    @staticmethod
    def _repo_key(owner: str, repo: str) -> str:
        return f"{owner}/{repo}".lower()

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/health":
            return self._send(200, {
                "ok": True, "name": "Mouse", "system": "Brain 3",
                "mode": "offline-emulator",
                "real_github": False, "render": False,
                "external_network": False, "physical_devices": False,
                "windows_boot_verified": False,
                "persistence": "memory-only",
                "unified_kernel": KERNEL.health(),
            })
        if path == "/api/brain3/kernel":
            return self._send(200, KERNEL.health())
        if path == "/api/brain/compatibility":
            return self._send(200, {
                "ok": True,
                "bridge": "mouse-local-compatibility-contract",
                "legacy_brain": {"accepted_as": "legacy_brain", "execution": False},
                "brain_v12": {"accepted_as": "brain_v12", "execution": False},
                "brain3": {"provider": "Mouse", "mode": "local-emulation"},
                "real_github": False, "render": False,
                "physical_devices": False, "windows_boot_verified": False,
                "note": "Compatibility metadata only; no remote Brain is contacted.",
            })
        if path == "/api/brain/tasks":
            return self._send(200, KERNEL.tasks())
        if path == "/api/repos":
            with STATE.lock:
                return self._send(200, [
                    {k: v for k, v in item.items() if k not in ("issues", "branches", "workflows")}
                    for item in STATE.repositories.values()
                ])
        match = re.fullmatch(r"/api/repos/([^/]+)/([^/]+)/(issues|branches|workflows)", path)
        if match:
            owner, repo, resource = match.groups()
            key = self._repo_key(owner, repo)
            with STATE.lock:
                item = STATE.repositories.get(key)
                if item is None:
                    return self._send(404, {"message": "Mouse repository not found"})
                return self._send(200, item[resource])
        return self._send(404, {"message": "Mouse endpoint not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            body = self._body()
        except ValueError as exc:
            return self._send(400, {"message": str(exc)})

        if path == "/api/brain/tasks":
            source = str(body.get("source", "")).strip().lower()
            action = str(body.get("action", "")).strip().lower()
            description = str(body.get("description", "")).strip()
            if source not in ALLOWED_SOURCES:
                return self._send(400, {"message": "source must be legacy_brain or brain_v12"})
            if action in BLOCKED_ACTIONS:
                return self._send(403, {
                    "message": "action blocked by Brain 3 policy",
                    "blocked_action": action,
                    "executed": False,
                })
            if action not in ALLOWED_ACTIONS:
                return self._send(400, {"message": "action must be inspect, test, or plan"})
            if not description or len(description) > 2000:
                return self._send(400, {"message": "description is required and must be at most 2000 characters"})
            try:
                task = KERNEL.submit(action, description, requested_by=source)
            except (ValueError, PermissionError) as exc:
                return self._send(403 if isinstance(exc, PermissionError) else 400, {"message": str(exc), "executed": False})
            task.update({
                "source": source,
                "emulated": True,
                "remote_calls": False,
                "render": False,
                "physical_devices": False,
                "windows_boot_verified": False,
            })
            return self._send(202, task)

        if path == "/api/repos":
            owner = str(body.get("owner", "mouse-local")).strip()
            name = str(body.get("name", "")).strip()
            if not owner or not name or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", name):
                return self._send(400, {"message": "valid owner and name are required"})
            key = self._repo_key(owner, name)
            with STATE.lock:
                if key in STATE.repositories:
                    return self._send(409, {"message": "Mouse repository already exists"})
                item = {
                    "id": len(STATE.repositories) + 1,
                    "full_name": f"{owner}/{name}",
                    "name": name,
                    "owner": owner,
                    "emulated": True,
                    "issues": [],
                    "branches": [{"name": "main", "protected": False}],
                    "workflows": [],
                }
                STATE.repositories[key] = item
            return self._send(201, {k: v for k, v in item.items() if k not in ("issues", "branches", "workflows")})

        match = re.fullmatch(r"/api/repos/([^/]+)/([^/]+)/issues", path)
        if match:
            owner, repo = match.groups()
            key = self._repo_key(owner, repo)
            title = str(body.get("title", "")).strip()
            if not title:
                return self._send(400, {"message": "issue title is required"})
            with STATE.lock:
                item = STATE.repositories.get(key)
                if item is None:
                    return self._send(404, {"message": "Mouse repository not found"})
                issue = {
                    "number": STATE.next_issue,
                    "title": title,
                    "body": str(body.get("body", "")),
                    "state": "open",
                    "html_url": f"mouse://{owner}/{repo}/issues/{STATE.next_issue}",
                    "emulated": True,
                }
                STATE.next_issue += 1
                item["issues"].append(issue)
            return self._send(201, issue)

        return self._send(404, {"message": "Mouse endpoint not found"})

    def do_PUT(self) -> None:
        self._send(405, {"message": "Mouse emulator is read/create-only; mutation endpoint unsupported"})

    def do_DELETE(self) -> None:
        self._send(405, {"message": "Mouse emulator does not support deletion"})


def main() -> None:
    host = os.getenv("MOUSE_HOST", "127.0.0.1")
    port = int(os.getenv("MOUSE_PORT", "8787"))
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise SystemExit("Mouse refuses non-loopback binding by default")
    server = ThreadingHTTPServer((host, port), MouseHandler)
    print(f"MOUSE_READY=1 name=Mouse host={host} port={port} real_github=false render=false external_network=false", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
