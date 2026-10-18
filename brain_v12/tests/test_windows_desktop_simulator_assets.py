"""Static integration checks for the browser-based Brain Windows simulator.

These tests guard the wiring between the desktop HTML, virtual file workspace,
and application manager. They do not replace real browser interaction tests.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"


class WindowsDesktopSimulatorAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (WEB / "windows-desktop-simulator.html").read_text(encoding="utf-8")
        cls.files = (WEB / "brain-windows-virtual-apps.js").read_text(encoding="utf-8")
        cls.apps = (WEB / "brain-windows-app-manager.js").read_text(encoding="utf-8")

    def test_virtual_file_api_loads_before_application_manager(self):
        files_script = '<script src="brain-windows-virtual-apps.js">'
        apps_script = '<script src="brain-windows-app-manager.js">'
        self.assertIn(files_script, self.html)
        self.assertIn(apps_script, self.html)
        self.assertLess(self.html.index(files_script), self.html.index(apps_script))

    def test_virtual_file_api_supports_basic_file_operations(self):
        self.assertIn("window.BrainVirtualFiles=", self.files)
        for method in ("list:function()", "read:function(name)", "write:function(name,value)", "remove:function(name)"):
            with self.subTest(method=method):
                self.assertIn(method, self.files)

    def test_notes_app_reads_and_writes_shared_virtual_notes_file(self):
        self.assertIn("window.BrainVirtualFiles.read('notes.txt')", self.apps)
        self.assertIn("window.BrainVirtualFiles.write('notes.txt',value)", self.apps)
        self.assertIn("brain-windows-notes-v1", self.apps)

    def test_start_menu_applications_launcher_opens_app_manager(self):
        self.assertIn("b.textContent.includes('التطبيقات')", self.apps)
        self.assertIn("open('app-manager')", self.apps)
        self.assertIn("render();open('app-manager')", self.apps)

    def test_simulated_environment_does_not_claim_real_windows_or_exe_support(self):
        self.assertIn("SIMULATED", self.html)
        self.assertIn("تشغيل ملفات EXE", self.html)
        self.assertIn("غير مدعوم", self.html)


if __name__ == "__main__":
    unittest.main()
