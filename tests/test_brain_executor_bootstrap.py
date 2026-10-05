import os
from pathlib import Path
import subprocess
import sys


def test_executor_bootstrap_creates_live_heartbeat(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["BRAIN_WORKER_ID"] = "brain-bootstrap-test"
    env["BRAIN_EXECUTOR_HEARTBEAT"] = str(tmp_path / "heartbeat.json")
    env["BRAIN_LOCAL_WORKER_ROOT"] = str(tmp_path / "worker")

    code = (
        "from brain_v12.local_worker.bootstrap_brain_executor import bootstrap;"
        "p=bootstrap();"
        "assert p['owner']=='brain';"
        "assert p['persistent'] is True"
    )
    subprocess.run([sys.executable, "-c", code], cwd=root, env=env, check=True)
    assert (tmp_path / "heartbeat.json").exists()
