from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from brain_git_platform.api.routes import BrainGitApi
from brain_git_platform.service import BrainGitError, health

api = BrainGitApi()

class BrainGitHandler(BaseHTTPRequestHandler):
    server_version = "BrainGit/0.2"

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length=int(self.headers.get("Content-Length","0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path=urlparse(self.path).path.rstrip("/")
        try:
            if path=="/api/v1/health":
                return self._send(200,health())
            parts=path.split("/")
            if len(parts)==7 and parts[:4]==["","api","v1","repos"] and parts[6]=="refs":
                return self._send(200,api.refs(parts[4],parts[5]))
            if len(parts)==6 and parts[:4]==["","api","v1","runs"]:
                return self._send(200,api.workflow(int(parts[4])))
        except (BrainGitError,ValueError) as exc:
            return self._send(404,{"error":str(exc)})
        return self._send(404,{"error":"not_found"})

    def do_POST(self):
        path=urlparse(self.path).path.rstrip("/")
        try:
            data=self._body()
        except (json.JSONDecodeError,ValueError):
            return self._send(400,{"error":"invalid_json"})
        try:
            if path=="/api/v1/repos":
                return self._send(201,api.create_repo(data["namespace"],data["name"],data.get("default_branch","main")))
            if path=="/api/v1/workflows/dispatch":
                return self._send(202,api.dispatch_workflow(data["namespace"],data["repository"],data["workflow"],data.get("ref","main")))
        except KeyError as exc:
            return self._send(400,{"error":f"missing:{exc.args[0]}"})
        except BrainGitError as exc:
            return self._send(409,{"error":str(exc)})
        return self._send(404,{"error":"not_found"})

def serve(host: str="127.0.0.1", port: int=8090):
    ThreadingHTTPServer((host,port),BrainGitHandler).serve_forever()

if __name__=="__main__":
    serve()
