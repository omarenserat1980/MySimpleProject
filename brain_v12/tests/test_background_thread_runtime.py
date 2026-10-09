from __future__ import annotations

import time
import unittest

from brain_v12.brain.background_thread_runtime import (
    BackgroundJobSpec,
    BackgroundThreadSupervisor,
)


class BackgroundThreadRuntimeTests(unittest.TestCase):
    def test_job_runs_and_stops_cleanly(self) -> None:
        runs: list[float] = []

        def job(stop) -> None:
            runs.append(time.time())

        supervisor = BackgroundThreadSupervisor(join_timeout_seconds=1)
        supervisor.register(BackgroundJobSpec("test", job, interval_seconds=0.01))
        supervisor.start()
        time.sleep(0.04)
        self.assertTrue(supervisor.is_alive("test"))
        supervisor.stop()
        self.assertFalse(supervisor.is_alive("test"))
        self.assertGreaterEqual(len(runs), 2)
        self.assertEqual(supervisor.snapshot()["jobs"]["test"]["state"], "STOPPED")

    def test_duplicate_registration_is_rejected(self) -> None:
        supervisor = BackgroundThreadSupervisor()
        spec = BackgroundJobSpec("same", lambda stop: None)
        supervisor.register(spec)
        with self.assertRaisesRegex(RuntimeError, "ALREADY_REGISTERED"):
            supervisor.register(spec)

    def test_crash_restarts_with_bounded_backoff(self) -> None:
        runs = 0

        def flaky(stop) -> None:
            nonlocal runs
            runs += 1
            if runs == 1:
                raise RuntimeError("expected-test-failure")

        supervisor = BackgroundThreadSupervisor(join_timeout_seconds=1)
        supervisor.register(
            BackgroundJobSpec(
                "flaky",
                flaky,
                interval_seconds=0.01,
                max_backoff_seconds=0.03,
            )
        )
        supervisor.start()
        time.sleep(0.06)
        supervisor.stop()
        state = supervisor.snapshot()["jobs"]["flaky"]
        self.assertGreaterEqual(state["restart_count"], 1)
        self.assertGreaterEqual(state["run_count"], 1)
        self.assertEqual(state["state"], "STOPPED")

    def test_register_after_start_is_rejected(self) -> None:
        supervisor = BackgroundThreadSupervisor()
        supervisor.register(BackgroundJobSpec("one", lambda stop: None))
        supervisor.start()
        try:
            with self.assertRaisesRegex(RuntimeError, "AFTER_START"):
                supervisor.register(BackgroundJobSpec("two", lambda stop: None))
        finally:
            supervisor.stop()


if __name__ == "__main__":
    unittest.main()
