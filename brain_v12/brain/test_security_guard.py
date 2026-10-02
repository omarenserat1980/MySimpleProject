import os,unittest
from brain_v12.brain.security_guard import SecurityGuard

class SecurityGuardTests(unittest.TestCase):
    def test_fail_closed_auth(self):
        old=os.environ.pop("BRAIN_CONTROL_KEY",None)
        try:self.assertFalse(SecurityGuard().authenticate("x"))
        finally:
            if old is not None: os.environ["BRAIN_CONTROL_KEY"]=old
    def test_constant_time_compare_path(self):
        os.environ["BRAIN_CONTROL_KEY"]="secret-test"
        try:self.assertTrue(SecurityGuard().authenticate("secret-test"))
        finally:os.environ.pop("BRAIN_CONTROL_KEY",None)
    def test_high_risk_requires_approval(self):
        g=SecurityGuard()
        self.assertFalse(g.authorize("code_execution",{"code_execution"}).allowed)
        self.assertTrue(g.authorize("code_execution",{"code_execution"},approved=True).allowed)
    def test_least_privilege(self):
        self.assertFalse(SecurityGuard().authorize("delete",{"read"}).allowed)
    def test_secret_exclusion(self):
        m=SecurityGuard().safe_metadata({"token":"hidden","name":"ok","api_key":"x"})
        self.assertEqual(m,{"name":"ok"})
    def test_deterministic_audit_fingerprint(self):
        g=SecurityGuard()
        self.assertEqual(g.audit_fingerprint({"b":2,"a":1}),g.audit_fingerprint({"a":1,"b":2}))

if __name__=="__main__": unittest.main()
