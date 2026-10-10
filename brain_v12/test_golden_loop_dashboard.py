from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.evidence_store import EvidenceStore


class GoldenLoopDashboardTests(unittest.TestCase):
    def test_read_only_evidence_query_returns_only_golden_events(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EvidenceStore(str(Path(directory) / "evidence.db"))
            try:
                store.append("task-1", "golden:intent", {"phase": "INTENT"}, "test")
                store.append("task-2", "execution", {"phase": "EXECUTE"}, "test")
                events = store.recent_golden(100)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["task_id"], "task-1")
                self.assertEqual(store.golden_count(), 1)
            finally:
                store.close()

    def test_app_exposes_read_only_golden_events_route(self):
        source = Path("brain_v12/app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "golden_loop_events":
                found = True
                self.assertTrue(any(
                    isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Attribute)
                    and d.func.attr == "get"
                    and d.args
                    and isinstance(d.args[0], ast.Constant)
                    and d.args[0].value == "/api/golden-loop/events"
                    for d in node.decorator_list
                ))
        self.assertTrue(found, "read-only Golden evidence endpoint is not wired")

    def test_a4_page_is_read_only_and_uses_evidence_api(self):
        page = Path("brain_v12/web/golden-loop.html").read_text(encoding="utf-8")
        self.assertIn('dir="rtl"', page)
        self.assertIn("@page{size:A4", page)
        self.assertIn("/api/golden-loop/events", page)
        self.assertIn("لا تُنشأ سجلات بديلة", page)
        self.assertNotIn("method:'POST'", page)
        self.assertNotIn("method: 'POST'", page)


if __name__ == "__main__":
    unittest.main()
