import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
UI = ROOT / "web" / "index.html"
PAGES = ROOT.parent / ".github" / "workflows" / "brain-pages.yml"


class ApiUiRoutingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = APP.read_text(encoding="utf-8")
        cls.ui = UI.read_text(encoding="utf-8")
        cls.pages = PAGES.read_text(encoding="utf-8")

    def test_cors_allows_browser_control_methods(self):
        self.assertIn('"DELETE"', self.app)
        self.assertIn('"OPTIONS"', self.app)
        self.assertIn('"X-BRAIN-CONTROL-KEY"', self.app)
        self.assertIn('"X-Brain-Control-Key"', self.app)

    def test_pages_require_a_real_api_origin(self):
        self.assertIn('BRAIN_API_ORIGIN is required', self.pages)
        self.assertIn('BRAIN_API_ORIGIN must use HTTPS', self.pages)

    def test_pages_install_api_bridge(self):
        self.assertIn('brain-api-bridge.js', self.pages)
        self.assertIn('window.fetch=function', self.pages)
        self.assertIn('input.startsWith("/api/")', self.pages)

    def test_pages_trigger_on_main_brain_ui_changes(self):
        self.assertIn('"brain_v12/web/index.html"', self.pages)
        self.assertIn('"brain_v12/web/**/*.html"', self.pages)

    def test_main_ui_has_real_api_actions(self):
        for endpoint in ("/api/system/connection", "/api/system/readiness",
                         "/api/cinema/status", "/api/cinema/start"):
            self.assertIn(endpoint, self.ui)

    def test_no_control_secret_is_baked_by_pages_workflow(self):
        self.assertNotRegex(self.pages, r'BRAIN_CONTROL_KEY.*json\.dumps')
        self.assertNotIn('BRAIN_CONTROL_KEY:', self.pages)


if __name__ == "__main__":
    unittest.main()
