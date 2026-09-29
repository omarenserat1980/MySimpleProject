import unittest
from brain_v12.app import app

class BrainCodeHubTests(unittest.TestCase):
    def test_routes(self):
        paths={getattr(r,"path","") for r in app.routes}
        for p in ("/api/brain-hub/config","/api/brain-hub/repositories","/api/brain-hub/branches","/api/brain-hub/issues","/api/brain-hub/pulls","/api/brain-hub/compare","/api/brain-hub/actions","/api/brain-hub/tree","/api/brain-hub/file"):
            self.assertIn(p,paths)
    def test_ui_mount(self):
        self.assertIn("/code-hub", {getattr(r,"path","") for r in app.routes})

if __name__=="__main__":
    unittest.main()
