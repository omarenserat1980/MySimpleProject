import unittest
from brain_v12.brain.brain_ai import BrainAI
from brain_v12.brain.github_tools import BrainGitHubTools

class TestGitHubToolRegistry(unittest.TestCase):
    def test_registry(self):
        p=type("P",(),{"status":lambda s:{}, "respond":lambda *a,**k:{"ok":True,"reply":"ok"}})()
        ai=BrainAI(p)
        BrainGitHubTools("omarenserat1980/MySimpleProject").register(ai)
        names={x["name"] for x in ai.status()["tools"]}
        self.assertIn("github.status",names)
        self.assertIn("github.get_file",names)
        self.assertIn("github.write_file",names)
        self.assertIn("github.merge_pull_request",names)

    def test_write_gate(self):
        p=type("P",(),{"status":lambda s:{}, "respond":lambda *a,**k:{"ok":True,"reply":"ok"}})()
        ai=BrainAI(p)
        BrainGitHubTools("omarenserat1980/MySimpleProject").register(ai)
        result=ai.execute_tool("github.create_issue",{"title":"test"})
        self.assertEqual(result["status"],"WAITING_APPROVAL")

if __name__=="__main__":
    unittest.main()
