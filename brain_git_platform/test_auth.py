import unittest
from brain_git_platform.auth.auth import issue_token, verify_token
class AuthTests(unittest.TestCase):
    def test_scoped_token(self):
        raw, record = issue_token("brain", {"repo:read"})
        self.assertTrue(verify_token(raw, record, "repo:read"))
        self.assertFalse(verify_token(raw, record, "repo:write"))
if __name__ == "__main__": unittest.main()
