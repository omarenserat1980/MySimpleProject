import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "brain-app-v2"

class BrainWebAppV2ContractTest(unittest.TestCase):
    def test_core_assets_exist(self):
        for name in ("index.html", "app.css", "app.js", "manifest.webmanifest", "sw.js", "version.json"):
            self.assertTrue((WEB / name).is_file(), name)

    def test_api_contracts_and_update_path(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        js = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn('serviceWorker.register("./sw.js"', html)
        for endpoint in ("/api/brain-ai/chat", "/api/brain-ai/status", "/api/media/upload", "/api/image-factory/generate"):
            self.assertIn(endpoint, js)
        self.assertIn("./version.json?ts=", js)
        self.assertIn("APP_VERSION_KEY", js)
        self.assertNotIn("BRAIN_GITHUB_TOKEN", js)

    def test_manifest_matches_version_file(self):
        manifest = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
        version = json.loads((WEB / "version.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], version["version"])
        self.assertEqual(manifest["name"], "Electronic Brain")

    def test_fastapi_mount_exists(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('/brain-app-v2', app)
        self.assertIn('web","brain-app-v2', app)

if __name__ == "__main__":
    unittest.main()