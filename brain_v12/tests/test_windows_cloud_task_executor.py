import unittest

from brain_v12.brain.windows_cloud_executor import CloudWindowsVM
from brain_v12.brain.windows_cloud_task_executor import WindowsCloudTaskExecutor


class WindowsCloudTaskExecutorTests(unittest.TestCase):
    def setUp(self):
        self.vm = CloudWindowsVM(
            vm_id="win-cloud-01", provider="azure", region="westeurope",
            state="RUNNING",
        )
        self.node = {
            "node_id": "win-cloud-01", "provider": "azure", "state": "READY",
            "architecture": "x86_64", "last_heartbeat": 990.0,
            "capabilities": [
                "windows-server-2025", "windows-cloud",
                "brain-task-execution", "brain-heartbeat", "brain-evidence",
            ],
        }
        self.calls = []
        self.jobs = [
            {"job_id": "job-1", "state": "QUEUED", "evidence": []},
            {"job_id": "job-1", "state": "RUNNING", "evidence": []},
            {"job_id": "job-1", "state": "SUCCESS", "evidence": [{"returncode": 0}]},
        ]

        def http(method, url, body, token):
            self.calls.append((method, url, body, token))
            if method == "POST":
                return {"ok": True, "job": self.jobs[0]}
            return {"ok": True, "job": self.jobs.pop(0)}

        self.http = http

    def test_verified_runtime_submits_and_waits_for_success(self):
        runner = WindowsCloudTaskExecutor(
            fabric_url="https://fabric.example",
            control_token="secret",
            http=self.http,
            sleep=lambda _: None,
        )
        result = runner.run(
            self.vm, self.node, ["cmd.exe", "/c", "echo", "hello"],
            timeout=30, now=1000.0,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["state"], "SUCCESS")
        self.assertEqual(result["executor"], "windows-server-2025-cloud")
        self.assertEqual(self.calls[0][0], "POST")
        self.assertNotIn("secret", str(result))

    def test_stale_runtime_blocks_before_job_creation(self):
        runner = WindowsCloudTaskExecutor(
            fabric_url="https://fabric.example",
            control_token="secret",
            http=self.http,
        )
        with self.assertRaisesRegex(RuntimeError, "WINDOWS_CLOUD_RUNTIME_NOT_VERIFIED"):
            runner.run(
                self.vm, {**self.node, "last_heartbeat": 800.0},
                ["cmd.exe"], now=1000.0,
            )
        self.assertEqual(self.calls, [])

    def test_no_fabric_url_blocks(self):
        runner = WindowsCloudTaskExecutor(control_token="secret", http=self.http)
        with self.assertRaisesRegex(RuntimeError, "BRAIN_FABRIC_URL_REQUIRED"):
            runner.run(self.vm, self.node, ["cmd.exe"], now=1000.0)


if __name__ == "__main__":
    unittest.main()
