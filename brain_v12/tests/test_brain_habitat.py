import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.habitat import CapabilityManager, ProjectFactory, SourceExplorer


class BrainHabitatTests(unittest.TestCase):
    def test_capability_manager_is_least_privilege(self):
        with tempfile.TemporaryDirectory() as td:
            mgr = CapabilityManager(Path(td) / "capabilities.json")
            self.assertFalse(mgr.allowed("app.open"))
            mgr.declare("app.open")
            self.assertTrue(mgr.allowed("app.open"))
            with self.assertRaises(ValueError):
                mgr.declare("root.shell")

    def test_project_factory_confines_projects(self):
        with tempfile.TemporaryDirectory() as td:
            result = ProjectFactory(td).create("Demo", "python")
            self.assertTrue(result["ok"])
            self.assertTrue((Path(td) / "Demo" / "tests" / "test_smoke.py").exists())
            with self.assertRaises(ValueError):
                ProjectFactory(td).create("../escape")

    def test_source_explorer_confines_reads(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "src"
            root.mkdir()
            source = root / "main.py"
            source.write_text("print('ok')\n", encoding="utf-8")
            explorer = SourceExplorer([root])
            self.assertIn(str(source), explorer.list_files())
            self.assertEqual(explorer.read(source), "print('ok')\n")
            with self.assertRaises(PermissionError):
                explorer.read(Path(td) / "outside.py")


if __name__ == "__main__":
    unittest.main()
