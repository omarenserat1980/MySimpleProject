import unittest
from brain_git_platform.runner.scheduler import BrainRunnerScheduler
class RunnerTests(unittest.TestCase):
    def test_queue_lifecycle(self):
        s=BrainRunnerScheduler()
        r=s.enqueue("brain/demo","verify.yml")
        self.assertEqual(r.status,"queued")
        claimed=s.claim()
        self.assertEqual(claimed.id,r.id)
        self.assertEqual(s.complete(r.id,True).status,"success")
if __name__ == "__main__": unittest.main()
