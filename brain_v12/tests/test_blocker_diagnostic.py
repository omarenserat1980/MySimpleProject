import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parents[1] / "brain" / "blocker_diagnostic.py"
spec = importlib.util.spec_from_file_location("blocker_diagnostic", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class BlockerDiagnosticTests(unittest.TestCase):
    def test_blocked_state_never_claims_boot(self):
        with patch.dict(os.environ, {}, clear=True):
            result = module.diagnose()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["windows_boot_verified"])
        self.assertGreater(result["summary"]["blockers"], 0)

    def test_secret_check_reports_names_not_values(self):
        with patch.dict(os.environ, {"EXAMPLE_SECRET_A": "top-secret-value"}, clear=True):
            result = module._check_env(("EXAMPLE_SECRET_A", "EXAMPLE_SECRET_B"), "TEST")
        self.assertEqual(result["missing_names"], ["EXAMPLE_SECRET_B"])
        self.assertNotIn("top-secret-value", str(result))

    def test_all_env_values_present(self):
        values = {name: "configured" for name in module.REGISTRY_ENV}
        with patch.dict(os.environ, values, clear=True):
            result = module._check_env(module.REGISTRY_ENV, "TEST")
        self.assertTrue(result["ok"])
        self.assertEqual(result["present_count"], len(module.REGISTRY_ENV))

if __name__ == "__main__":
    unittest.main()
