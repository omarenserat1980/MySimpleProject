import tempfile, unittest
from pathlib import Path
from brain_git_platform.audit import AuditLog
from brain_git_platform.api.auth_middleware import require_scope, AUTHORITY

class SecurityTests(unittest.TestCase):
    def test_scoped_auth_and_audit(self):
        token=AUTHORITY.issue("runner",{"workflow:run"})
        self.assertTrue(require_scope({"Authorization":"Bearer "+token},"workflow:run").ok)
        self.assertFalse(require_scope({"Authorization":"Bearer "+token},"repo:write").ok)
        with tempfile.TemporaryDirectory() as d:
            event=AuditLog(Path(d)).record("runner","workflow.dispatch","brain/test")
            self.assertEqual(event["outcome"],"success")
            self.assertTrue((Path(d)/"audit.jsonl").exists())

if __name__=="__main__": unittest.main()