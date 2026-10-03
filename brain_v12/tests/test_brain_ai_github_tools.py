import unittest
from brain_v12.brain.brain_ai import BrainAI

class Provider:
    def status(self): return {"ok": True}
    def respond(self, *args, **kwargs): return {"ok": True, "reply": "ok", "provider": "fake", "model": "fake"}

class FakeGitHub:
    def capability_catalog(self): return {"ok": True, "domains": ["repositories", "issues", "actions"]}
    def repository(self, owner, repo): return {"full_name": f"{owner}/{repo}"}
    def contents(self, owner, repo, path="", ref=None): return {"path": path, "ref": ref}
    def issues(self, owner, repo, number=None): return {"number": number}
    def pull_request(self, owner, repo, number): return {"number": number}
    def actions_runs(self, owner, repo, page=1, per_page=30): return {"page": page, "per_page": per_page}
    def releases(self, owner, repo): return []
    def search(self, query, search_type="repositories"): return {"query": query, "type": search_type}
    def write_contents(self, owner, repo, path, body, approved=False): return {"written": approved}

class BrainAIToolTests(unittest.TestCase):
    def setUp(self):
        self.ai = BrainAI(Provider(), github=FakeGitHub())

    def test_github_tools_are_registered(self):
        self.assertIn("github.repository", self.ai.tools)
        self.assertIn("github.actions_runs", self.ai.tools)

    def test_read_tool_executes(self):
        result = self.ai.execute_tool("github.repository", {"owner": "o", "repo": "r"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["full_name"], "o/r")

    def test_tool_failure_is_retried_and_verified(self):
        attempts = {"n": 0}
        def flaky(_):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("transient")
            return {"ok": True, "status": "COMPLETED"}
        self.ai.register_tool("flaky", "test retry", flaky)
        class RetryProvider:
            def status(self): return {"ok": True}
            def respond(self, *args, **kwargs):
                if not hasattr(self, "done"):
                    self.done = True
                    return {"ok": True, "provider": "fake", "model": "fake",
                            "tool_calls": [{"name": "flaky", "params": {}}]}
                return {"ok": True, "provider": "fake", "model": "fake", "reply": "recovered"}
        self.ai.provider = RetryProvider()
        result = self.ai.chat("retry this")
        self.assertTrue(result.ok)
        self.assertEqual(result.tool_calls[0]["retry_count"], 1)
        self.assertTrue(result.tool_calls[0]["verified"])

    def test_write_requires_approval(self):
        result = self.ai.execute_tool("github.write_contents", {"owner":"o","repo":"r","path":"x","body":{}}, approved=False)
        self.assertEqual(result["status"], "WAITING_APPROVAL")

if __name__ == "__main__":
    unittest.main()
