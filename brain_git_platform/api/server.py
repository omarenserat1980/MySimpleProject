from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from brain_git_platform.service import Repository, BrainGitError, create_repository, repository_path, health

class BrainGitHandler(BaseHTTPRequestHandler):
    server_version = "BrainGit/0.1"

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")
        if path == "/api/v1/health":
            return self._send(200, health())
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        length = int(self.headers.get("Content-Length", "0"))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "invalid_json"})

        if path == "/api/v1/repos":
            namespace, name = data.get("namespace"), data.get("name")
            if not namespace or not name:
                return self._send(400, {"error": "namespace_and_name_required"})
            try:
                p = create_repository(Repository(namespace, name, data.get("default_branch", "main")))
                return self._send(201, {"namespace": namespace, "name": name, "path": str(p)})
            except BrainGitError as exc:
                return self._send(409, {"error": str(exc)})
        self._send(404, {"error": "not_found"})

def serve(host: str = "127.0.0.1", port: int = 8090):
    ThreadingHTTPServer((host, port), BrainGitHandler).serve_forever()

if __name__ == "__main__":
    serve()
