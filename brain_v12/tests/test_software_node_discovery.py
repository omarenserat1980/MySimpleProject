"""Contract tests for read-only software-node discovery."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain import software_node_discovery as discovery


class SoftwareNodeDiscoveryTests(unittest.TestCase):
    def test_inventory_has_explicit_read_only_safety_boundaries(self):
        report = discovery.discover()
        self.assertEqual(report["mode"], "READ_ONLY_LOCAL_DISCOVERY")
        self.assertFalse(report["safety"]["network_probed"])
        self.assertFalse(report["safety"]["processes_started"])
        self.assertFalse(report["safety"]["secrets_read"])
        self.assertFalse(report["safety"]["mining_active_claimed"])
        self.assertIn("python_modules", report)
        self.assertIn("executables", report)
        self.assertIn("brain_components", report)
        self.assertIn("source_inventory", report)

    def test_module_probe_reports_presence_without_importing_module(self):
        with patch.object(discovery.importlib.util, "find_spec", return_value=None):
            self.assertEqual(discovery._module_status("example"), {
                "name": "example", "available": False
            })

    def test_component_probe_only_reports_file_presence(self):
        with patch.object(Path, "is_file", return_value=False):
            self.assertEqual(
                discovery._component_status("brain_v12/example.py"),
                {"path": "brain_v12/example.py", "present": False},
            )

    def test_source_inventory_is_bounded_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brain").mkdir()
            (root / "brain" / "z.py").write_text("# z", encoding="utf-8")
            (root / "brain" / "a.py").write_text("# a", encoding="utf-8")
            with patch.object(discovery, "ROOT", root), patch.object(
                discovery, "SOURCE_ROOTS", ("brain",)
            ):
                report = discovery._source_inventory()
        self.assertEqual(report["python_file_count"], 2)
        self.assertEqual(report["python_files"], ["brain/a.py", "brain/z.py"])
        self.assertFalse(report["truncated"])

    def test_output_refuses_to_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "inventory.json"
            target.write_text('{"keep": true}', encoding="utf-8")
            with self.assertRaises(SystemExit):
                discovery.main(["--output", str(target)])
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"keep": True})


if __name__ == "__main__":
    unittest.main()
