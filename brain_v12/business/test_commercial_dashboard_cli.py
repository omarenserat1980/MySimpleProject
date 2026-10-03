"""Test the read-only commercial dashboard CLI."""
import json
import subprocess
import sys
import unittest


class CommercialDashboardCLITests(unittest.TestCase):
    def test_cli_outputs_machine_readable_zero_revenue_initial_state(self):
        result = subprocess.run(
            [sys.executable, "-m", "brain_v12.business.commercial_dashboard_cli"],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["dashboard_type"], "BRAIN_COMMERCIAL_OPERATIONS")
        self.assertEqual(payload["capabilities"], 5)
        self.assertEqual(payload["verified_revenue"], 0.0)
        self.assertEqual(payload["verified_profit"], 0.0)
        self.assertTrue(payload["engineering_green_is_not_revenue"])


if __name__ == "__main__":
    unittest.main()
