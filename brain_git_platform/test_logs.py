from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from brain_git_platform.runner.logs import RunLog


class RunLogTests(unittest.TestCase):
    def test_append_and_read(self):
        with tempfile.TemporaryDirectory() as d:
            log = RunLog(Path(d))
            log.append(7, "stdout", "hello")
            log.append(7, "stderr", "failure\n")
            self.assertIn("hello", log.read(7, "stdout"))
            self.assertIn("failure", log.read(7, "stderr"))


if __name__ == "__main__":
    unittest.main()
