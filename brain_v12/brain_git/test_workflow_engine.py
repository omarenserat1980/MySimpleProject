import tempfile,unittest,sys
from pathlib import Path
from .workflow_engine import BrainWorkflowEngine
class WorkflowTests(unittest.TestCase):
    def test_independent_execution(self):
        with tempfile.TemporaryDirectory() as d:
            class Gateway:
                def run(self, argv, capability, cwd=None, timeout=None):
                    return {
                        "ok": True, "returncode": 0, "stdout": "BRAIN_WORKFLOW_OK",
                        "stderr": "", "executor": "brain-internal",
                        "authority": "brain-internal", "verified_executor": True,
                    }
            e=BrainWorkflowEngine(d, execution_gateway=Gateway())
            x=e.create("proof",[sys.executable,"-c","print('BRAIN_WORKFLOW_OK')"])
            y=e.run(x)
            self.assertEqual(y["status"],"SUCCESS")
            self.assertEqual(y["returncode"],0)
            self.assertIn("BRAIN_WORKFLOW_OK",y["stdout"])
if __name__=="__main__": unittest.main()
