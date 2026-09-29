from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from brain_git_platform.api.auth_middleware import require_scope
from brain_git_platform.api.routes import BrainGitApi
from brain_git_platform.service import BrainGitError, health

api = BrainGitApi()


class BrainGitHandler(BaseHTTPRequestHandler):
    server_version = "BrainGit/0.6"

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorize(self, scope: str) -> bool:
        result = require_scope(dict(self.headers.items()), scope)
        if result.ok:
            return True
        code = 503 if result.error == "authentication_not_configured" else (
            401 if result.error == "authentication_required" else 403
        )
        self._send(code, {"error": result.error})
        return False

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 2_000_000:
            raise ValueError("request_too_large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")
        if path != "/api/v1/health" and not self._authorize("repo:read"):
            return
        try:
            if path == "/api/v1/health":
                return self._send(200, health())
            parts = path.split("/")
            if len(parts) == 7 and parts[:4] == ["", "api", "v1", "repos"] and parts[6] == "refs":
                return self._send(200, api.refs(parts[4], parts[5]))
            if len(parts) == 5 and parts[:4] == ["", "api", "v1", "runs"]:
                return self._send(200, api.workflow(int(parts[4])))
            if len(parts) == 6 and parts[:4] == ["", "api", "v1", "runs"] and parts[5] in {"stdout", "stderr"}:
                return self._send(200, api.run_logs(int(parts[4]), parts[5]))
            if len(parts) == 7 and parts[:4] == ["", "api", "v1", "runs"] and parts[5] == "artifacts":
                return self._send(200, api.artifact(int(parts[4]), parts[6]))
        except (BrainGitError, ValueError, FileNotFoundError) as exc:
            return self._send(404, {"error": str(exc)})
        return self._send(404, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        scope = "repo:write"
        if path in {"/api/v1/workflows/dispatch", "/api/v1/workflows/cancel", "/api/v1/workflows/retry"}:
            scope = "workflow:write"
        elif path.startswith("/api/v1/pulls"):
            scope = "pull:write"
        if not self._authorize(scope):
            return
        try:
            data = self._body()
        except (json.JSONDecodeError, ValueError):
            return self._send(400, {"error": "invalid_request"})

        try:
            if path == "/api/v1/repos":
                return self._send(201, api.create_repo(data["namespace"], data["name"], data.get("default_branch", "main")))
            if path == "/api/v1/workflows/dispatch":
                return self._send(202, api.dispatch_workflow(data["namespace"], data["repository"], data["workflow"], data.get("ref", "main")))
            if path == "/api/v1/workflows/cancel":
                return self._send(200, api.cancel_workflow(int(data["run_id"])))
            if path == "/api/v1/workflows/retry":
                return self._send(202, api.retry_workflow(int(data["run_id"])))
            if path == "/api/v1/pulls":
                return self._send(201, api.create_pr(data["namespace"], data["repository"], data["source"], data["target"], data["title"]))
            if path == "/api/v1/pulls/merge":
                return self._send(200, api.merge_pr(int(data["pull_request_id"])))
            if path == "/api/v1/pulls/close":
                return self._send(200, api.close_pr(int(data["pull_request_id"])))
        except KeyError as exc:
            return self._send(400, {"error": f"missing:{exc.args[0]}"})
        except (TypeError, ValueError) as exc:
            return self._send(400, {"error": str(exc)})
        except BrainGitError as exc:
            return self._send(409, {"error": str(exc)})
        return self._send(404, {"error": "not_found"})


def serve(host: str = "127.0.0.1", port: int = 8090):
    ThreadingHTTPServer((host, port), BrainGitHandler).serve_forever()


if __name__ == "__main__":
    serve()
