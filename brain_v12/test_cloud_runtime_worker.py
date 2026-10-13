"""Regression tests for truthful cloud-worker shutdown attestation."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from brain_v12.cloud_runtime import worker


class CloudRuntimeWorkerTests(unittest.TestCase):
    def test_requested_shutdown_writes_stopped_heartbeat_without_claiming_running(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "cloud-runtime"
            stop_event = threading.Event()
            stop_event.set()
            preflight = SimpleNamespace(
                verified=True,
                reasons=[],
                evidence=lambda: {"verified": True, "reasons": []},
            )
            env = {
                "BRAIN_RUNTIME_HOME": directory,
                "BRAIN_RUNTIME_ROOT": str(root),
                "BRAIN_INTERNAL_RUNNER_FLAG": "1",
                "BRAIN_WORKER_POLL_SECONDS": "1",
                "BRAIN_TASK_TIMEOUT": "10",
            }
            with patch.dict(os.environ, env, clear=False), \
                 patch.object(worker, "inspect_runner", return_value=preflight), \
                 patch.object(worker, "InternalTaskRuntime") as runtime_type:
                worker.run_forever(stop_event=stop_event)

            payload = json.loads((root / "cloud-worker-heartbeat.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "STOPPED")
            self.assertEqual(payload["service"], "brain-cloud-runtime")
            runtime_type.assert_called_once_with(root)
            runtime_type.return_value.run_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
