#!/usr/bin/env python3
"""Mouse: an offline GitHub-shaped API emulator for Brain 3.

This service is deliberately local-only, in-memory, and non-authoritative.
It never calls GitHub, Render, or any remote service.
"""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlparse


class MouseState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.repositories: dict[str, dict] = {}
        self.next_issue = 1

    def reset(self) -> None:
        with self.lock:
            self.repositories.clear()
            self.next_issue = 1


STATE = MouseState()


class MouseHandler(BaseHTTPRequestHandler):
    server_version = "MouseGitHubEmulator/0.1"

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
                "mode": "offline-github-emulator",
                "real_github": False, "render": False,
                "persistence": "memory-only",
            })
        if path == "/api/repos":
            with STATE.lock:
                return self._send(200, list(STATE.repositories.values()))
        match = re.fullmatch(r"/api/repos/([^/]+)/([^/]+)/(issues|branches|workflows)", path)
        if match:
            owner, repo, resource = match.groups()
            key = self._repo_key(owner, repo)
            with STATE.lock:
                item = STATE.repositories.get(key)
                if item is None:
                    return self._send(404, {"message": "Mouse repository not found"})
                if resource == "issues":
                    return self._send(200, item["issues"])
                if resource == "branches":
                    return self._send(200, item["branches"])
                return self._send(200, item["workflows"])
        return self._send(404, {"message": "Mouse endpoint not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            body = self._body()
        except ValueError as exc:
            return self._send(400, {"message": str(exc)})

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
    print(f"MOUSE_READY=1 name=Mouse host={host} port={port} real_github=false render=false", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
