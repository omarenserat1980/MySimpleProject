import unittest
from brain_v12.app import app

class BrainCodeHubTests(unittest.TestCase):
    def test_routes(self):
        paths={getattr(r,"path","") for r in app.routes}
        for p in ("/api/brain-hub/config","/api/brain-hub/repositories","/api/brain-hub/branches","/api/brain-hub/issues","/api/brain-hub/pulls","/api/brain-hub/compare","/api/brain-hub/actions","/api/brain-hub/tree","/api/brain-hub/file","/api/brain-hub/search","/api/brain-hub/pulls/{number}/merge","/api/brain-hub/issues/{number}/close","/api/brain-hub/actions/{run_id}/jobs"):
            self.assertIn(p,paths)
    def test_ui_mount(self):
        self.assertIn("/code-hub", {getattr(r,"path","") for r in app.routes})

    def test_write_routes_are_protected(self):
        source=__import__("pathlib").Path(__file__).resolve().parents[1]/"app.py"
        text=source.read_text(encoding="utf-8")
        for marker in (
            'def brain_hub_create_repository(request:Request',
            'def brain_hub_create_branch(request:Request',
            'def brain_hub_create_issue(request:Request',
            'def brain_hub_create_pull(request:Request',
            'def brain_hub_cancel_action(run_id:int, request:Request',
            'def brain_hub_rerun_action(run_id:int, request:Request',
            'def brain_hub_merge_pull(number:int, request:Request',
            'def brain_hub_close_issue(number:int, request:Request',
        ):
            self.assertIn(marker,text)
        self.assertGreaterEqual(text.count("require_control_key(request)"), 8)

    def test_ui_controls(self):
        source=__import__("pathlib").Path(__file__).resolve().parents[1]/"web"/"code-hub"/"index.html"
        text=source.read_text(encoding="utf-8")
        for marker in ("controlKey","closeIssue","mergePR","showJobs","actionRun"):
            self.assertIn(marker,text)

if __name__=="__main__":
    unittest.main()
