import tempfile, unittest
from brain_git_platform import service
from brain_git_platform.workflows import dispatch,set_status,get_run

class WorkflowTests(unittest.TestCase):
    def test_dispatch_lifecycle(self):
        with tempfile.TemporaryDirectory() as d:
            old=service.ROOT
            try:
                service.ROOT=__import__("pathlib").Path(d)
                service.DB=service.ROOT/"brain-git.db"
                service.initialize()
                run=dispatch("brain","test","verification","main")
                self.assertEqual(get_run(run.id)["status"],"queued")
                set_status(run.id,"running")
                set_status(run.id,"success")
                self.assertEqual(get_run(run.id)["status"],"success")
            finally:
                service.ROOT=old
                service.DB=old/"brain-git.db"

if __name__=="__main__": unittest.main()
