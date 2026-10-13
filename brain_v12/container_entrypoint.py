"""Container supervisor for the Brain API and its software-only worker."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = os.getenv("PORT", "10000")
API_URL = f"http://127.0.0.1:{PORT}/health"
# Existing service URL only; no new service or credential is created.
os.environ.setdefault("BRAIN_ORIGIN", "https://brain-control-plane-main.onrender.com")


def wait_for_api(process: subprocess.Popen, timeout: float = 45.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and process.poll() is None:
        try:
            with urllib.request.urlopen(API_URL, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1)
    return False


def main() -> int:
    api = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "brain_v12.mcp_server:app",
        "--host", "0.0.0.0", "--port", PORT,
    ])
    worker = None

    def shutdown(_signum=None, _frame=None):
        for proc in (worker, api):
            if proc is not None and proc.poll() is None:
                proc.terminate()
        for proc in (worker, api):
            if proc is not None:
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    if not wait_for_api(api):
        shutdown()
        return 1

    worker = subprocess.Popen([sys.executable, "-m", "brain_v12.cloud_worker_agent"])
    while True:
        api_code = api.poll()
        worker_code = worker.poll()
        if api_code is not None or worker_code is not None:
            shutdown()
            # Either process exiting means the supervised container should restart.
            return api_code if api_code is not None else (worker_code or 1)


if __name__ == "__main__":
    raise SystemExit(main())
