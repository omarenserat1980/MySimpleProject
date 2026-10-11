"""Regression tests for the read-only Brain memory path audit."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("audit_brain_memory_paths.py")
SPEC = importlib.util.spec_from_file_location("brain_memory_audit", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(AUDIT)


class AuditPatternTests(unittest.TestCase):
    def test_memory_store_pattern_matches(self):
        self.assertRegex("class MemoryStore:", AUDIT.PATTERNS["memory_store"])

    def test_sqlite_pattern_matches(self):
        self.assertRegex("sqlite3.connect('brain.db')", AUDIT.PATTERNS["sqlite_paths"])

    def test_runtime_path_pattern_matches_database_configuration(self):
        self.assertRegex("os.getenv(\"BRAIN_DB\")", AUDIT.PATTERNS["runtime_path_config"])

    def test_runtime_path_pattern_matches_path_initializer(self):
        self.assertRegex("configure_runtime_paths()", AUDIT.PATTERNS["runtime_path_config"])

    def test_api_route_pattern_matches_memory_route(self):
        self.assertRegex('@router.post("/api/memory/write")', AUDIT.PATTERNS["api_routes"])

    def test_quran_pattern_matches_arabic_reference(self):
        self.assertRegex("مراجعة آيات من القرآن الكريم", AUDIT.PATTERNS["quran_references"])

    def test_unrelated_text_does_not_match_quran_pattern(self):
        self.assertIsNone(AUDIT.PATTERNS["quran_references"].search("ordinary memory cache"))

    def test_scan_ignores_non_text_and_skipped_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "brain_v12").mkdir()
            (root / "brain_v12" / "memory.py").write_text("class MemoryStore:\n", encoding="utf-8")
            (root / "brain_v12" / "image.png").write_bytes(b"not text")
            (root / "brain_v12" / "__pycache__").mkdir()
            (root / "brain_v12" / "__pycache__" / "ignored.py").write_text("class MemoryStore:\n", encoding="utf-8")
            original_root, original_roots = AUDIT.ROOT, AUDIT.SEARCH_ROOTS
            try:
                AUDIT.ROOT = root
                AUDIT.SEARCH_ROOTS = (root / "brain_v12", root / "docs")
                files = list(AUDIT.iter_files())
                self.assertEqual([p.name for p in files], ["memory.py"])
            finally:
                AUDIT.ROOT, AUDIT.SEARCH_ROOTS = original_root, original_roots


if __name__ == "__main__":
    unittest.main(verbosity=2)
