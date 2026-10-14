import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class DesignFactoryCliTests(unittest.TestCase):
    def test_cli_emits_plan_json_and_never_claims_execution(self):
        result = subprocess.run(
            [sys.executable, "-m", "brain_v12.design_factory", "Bitcoin ASIC RTL and OpenROAD physical design"],
            cwd=ROOT, text=True, capture_output=True, check=False, timeout=10,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["status"], "PLANNED")
        self.assertFalse(plan["execution_started"])
        self.assertIn("G7_PHYSICAL", plan["required_gates"])
        self.assertTrue(any(p["id"] == "06" for p in plan["selected_prompts"]))

if __name__ == "__main__":
    unittest.main()
