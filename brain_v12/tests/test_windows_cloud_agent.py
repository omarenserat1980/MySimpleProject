import unittest
from unittest.mock import patch

from brain_v12 import cloud_windows_agent as agent


class WindowsCloudAgentTests(unittest.TestCase):
    def test_execute_job_requires_windows(self):
        with patch.object(agent.os, "name", "posix"):
            with self.assertRaisesRegex(RuntimeError, "WINDOWS_AGENT_REQUIRES_WINDOWS"):
                agent.execute_job({"payload": {"argv": ["cmd", "/c", "echo", "x"]}})

    def test_execute_job_rejects_non_argv_payload(self):
        with patch.object(agent.os, "name", "nt"):
            with self.assertRaisesRegex(RuntimeError, "WINDOWS_JOB_REQUIRES_ARGV_LIST"):
                agent.execute_job({"payload": {"command": "echo x"}})

    def test_execute_job_disables_shell(self):
        completed = type("Completed", (), {
            "returncode": 0, "stdout": "ok", "stderr": ""
        })()
        with patch.object(agent.os, "name", "nt"), patch.object(
            agent.subprocess, "run", return_value=completed
        ) as run:
            result = agent.execute_job({
                "payload": {"argv": ["cmd.exe", "/c", "echo", "ok"], "timeout_seconds": 10}
            })
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["shell"])
        self.assertEqual(run.call_args.kwargs["shell"], False)
        self.assertEqual(run.call_args.kwargs["check"], False)


if __name__ == "__main__":
    unittest.main()
