from __future__ import annotations

import threading
import time
import unittest

from brain_git_platform.runner.scheduler import BrainRunnerScheduler


class SchedulerLoopTests(unittest.TestCase):
    def test_worker_processes_queued_run(self):
        scheduler = BrainRunnerScheduler()
        seen = threading.Event()

        def handler(run):
            seen.set()
            return True

        scheduler.start(handler)
        run = scheduler.enqueue("brain/demo", "test")
        self.assertTrue(seen.wait(2))
        for _ in range(20):
            if scheduler.get(run.id).status == "success":
                break
            time.sleep(0.01)
        self.assertEqual(scheduler.get(run.id).status, "success")
        scheduler.stop()


if __name__ == "__main__":
    unittest.main()
