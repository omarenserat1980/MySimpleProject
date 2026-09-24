import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "web" / "index.html"

EXPECTED_VIEWS = {
    "home", "overview", "chat", "thinking", "goals", "memory", "permissions",
    "vision", "voice", "video", "chatgpt", "ai", "tools", "agent", "evolve",
    "workforce", "events",
}

class HumanInterfaceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = UI.read_text(encoding="utf-8")

    def test_all_human_views_exist(self):
        found = set(re.findall(r'<[^>]+id=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*\bview\b[^"\']*["\'][^>]*>', self.html))
        found |= set(re.findall(r'<[^>]+class=["\'][^"\']*\bview\b[^"\']*["\'][^>]*id=["\']([^"\']+)["\'][^>]*>', self.html))
        self.assertEqual(EXPECTED_VIEWS, found)

    def test_navigation_points_to_existing_views(self):
        nav = set(re.findall(r'data-view=["\']([^"\']+)["\']', self.html))
        self.assertTrue(EXPECTED_VIEWS.issubset(nav))
        self.assertTrue(nav.issubset(EXPECTED_VIEWS))

    def test_all_javascript_dom_references_exist(self):
        ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', self.html))
        refs = set(re.findall(r'\$\(["\']([^"\']+)["\']\)', self.html))
        self.assertEqual(set(), refs - ids)

    def test_overview_and_cycle_required_elements_exist(self):
        ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', self.html))
        for required in {"ovReadiness", "ovReadinessDetail", "goalText", "runBadge", "cycleOut"}:
            self.assertIn(required, ids)

    def test_nav_binding_does_not_override_non_navigation_buttons(self):
        self.assertNotIn("document.querySelectorAll('.nav button').forEach(b=>b.onclick=()=>show(b.dataset.view))", self.html)
        self.assertIn("button[data-view]", self.html)

    def test_api_gets_are_cache_busted(self):
        self.assertIn("cache:'no-store'", self.html)
        self.assertIn("_v12=", self.html)

    def test_human_command_input_exists(self):
        self.assertIn("قل للعقل ما تريد", self.html)

    def test_inline_handlers_reference_existing_functions(self):
        funcs = set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', self.html))
        handlers = re.findall(r"""onclick=["']([^"']+)["']""", self.html)
        allowed = {
            "show", "selectAIMode", "evolveBrain", "speakLast", "clearChat", "quick",
            "toggleVoice", "sendChat", "requestMic", "requestCamera", "stopCamera",
            "capture", "uploadFile", "runCycle", "addGoal", "learn", "checkPermissions",
            "loadWorkforce", "loadIncome", "loadEvents", "clearChatGPT", "sendChatGPT",
            "quickChatGPT", "uploadAny", "loadCaps", "loadAgent", "loadAI", "loadEvolve",
            "openCommandPalette", "closeCommandPalette", "filterCommands"
        }
        for handler in handlers:
            name = re.match(r'([A-Za-z_$][\w$]*)\s*\(', handler)
            if name and name.group(1) in allowed:
                self.assertIn(name.group(1), funcs, handler)

    def test_readiness_and_overview_are_wired(self):
        self.assertIn("/api/system/overview", self.html)
        self.assertIn("/api/system/readiness", self.html)
        self.assertIn("ovReadiness", self.html)

if __name__ == "__main__":
    unittest.main()
