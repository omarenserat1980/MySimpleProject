import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "web" / "index.html"

EXPECTED_VIEWS = {
    "home","overview","chat","thinking","goals","memory","permissions",
    "vision","voice","video","chatgpt","ai","tools","agent","evolve",
    "workforce","events",
}

class HumanInterfaceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = UI.read_text(encoding="utf-8")

    def test_all_human_views_exist(self):
        found = set(re.findall(r'<[^>]+id=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*\\bview\\b[^"\']*["\'][^>]*>', self.html))
        found |= set(re.findall(r'<[^>]+class=["\'][^"\']*\\bview\\b[^"\']*["\'][^>]*id=["\']([^"\']+)["\'][^>]*>', self.html))
        self.assertEqual(EXPECTED_VIEWS, found)

    def test_navigation_points_to_existing_views(self):
        nav = set(re.findall(r'data-view=["\']([^"\']+)["\']', self.html))
        self.assertTrue(EXPECTED_VIEWS.issubset(nav))

    def test_human_command_input_exists(self):
        self.assertIn("قل للعقل ما تريد", self.html)

    def test_readiness_and_overview_are_wired(self):
        self.assertIn("/api/system/overview", self.html)
        self.assertIn("/api/system/readiness", self.html)
        self.assertIn("ovReadiness", self.html)

if __name__ == "__main__":
    unittest.main()
