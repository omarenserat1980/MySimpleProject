import tempfile, unittest
from pathlib import Path
from brain_git_platform.runner.executor import BrainRunnerExecutor

class ExecutorTests(unittest.TestCase):
    def test_python_step(self):
        with tempfile.TemporaryDirectory() as d:
            result=BrainRunnerExecutor(Path(d)).run_step(["python","-c","print('brain-runner-ok')"])
            self.assertEqual(result.returncode,0)
            self.assertIn("brain-runner-ok",result.stdout)

if __name__=="__main__": unittest.main()
