import tempfile, unittest
from pathlib import Path
from brain_git_platform import service
from brain_git_platform.api.routes import BrainGitApi

class ApiTests(unittest.TestCase):
    def test_repo_refs_workflow_contract(self):
        with tempfile.TemporaryDirectory() as d:
            old_root,old_db=service.ROOT,service.DB
            try:
                service.ROOT=Path(d); service.DB=service.ROOT/"brain-git.db"
                api=BrainGitApi()
                created=api.create_repo("brain","api-test")
                self.assertTrue(created["ok"])
                self.assertEqual(api.refs("brain","api-test")["data"]["refs"],[])
                run=api.dispatch_workflow("brain","api-test","verification")
                self.assertEqual(run["data"]["run"]["status"],"queued")
                self.assertEqual(api.workflow(run["data"]["run"]["id"])["data"]["status"],"queued")
            finally:
                service.ROOT,service.DB=old_root,old_db

if __name__=="__main__": unittest.main()
