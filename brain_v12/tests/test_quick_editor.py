import ast
import json
import os
import unittest

os.environ.setdefault("BRAIN_DB", "/tmp/brain_quick_editor_test.db")

from brain_v12.app import _quick_editor_path, _quick_editor_validate, _github_config


class QuickEditorTests(unittest.TestCase):
    def test_path_allowlist(self):
        self.assertEqual(_quick_editor_path("brain_v12/app.py"), "brain_v12/app.py")
        with self.assertRaises(Exception):
            _quick_editor_path("../secrets.txt")
        with self.assertRaises(Exception):
            _quick_editor_path("etc/passwd")

    def test_python_validation(self):
        good = _quick_editor_validate("brain_v12/example.py", "x = 1\nprint(x)\n")
        self.assertTrue(good["ok"])
        bad = _quick_editor_validate("brain_v12/example.py", "def broken(:\n")
        self.assertFalse(bad["ok"])
        self.assertTrue(any("PYTHON_SYNTAX" in x for x in bad["errors"]))

    def test_json_validation(self):
        self.assertTrue(_quick_editor_validate("brain_v12/example.json", '{"ok": true}')["ok"])
        self.assertFalse(_quick_editor_validate("brain_v12/example.json", '{"ok": }')["ok"])

    def test_render_warning(self):
        result = _quick_editor_validate("brain_v12/example.py", "x = 'RENDER'")
        self.assertIn("LEGACY_RENDER_REFERENCE", result["warnings"])

    def test_github_config_is_safe(self):
        cfg = _github_config()
        self.assertEqual(cfg["repository"], "omarenserat1980/MySimpleProject")
        self.assertNotIn("token", cfg)


if __name__ == "__main__":
    unittest.main()
