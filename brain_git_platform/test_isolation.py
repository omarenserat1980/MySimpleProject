from __future__ import annotations

import unittest
from pathlib import Path

from brain_git_platform.isolation import scan_runtime_tree


class IsolationTests(unittest.TestCase):
    def test_runtime_tree_is_github_free(self):
        findings = scan_runtime_tree(Path(__file__).parent)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
