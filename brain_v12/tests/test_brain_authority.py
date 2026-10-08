import unittest
from brain_v12.brain.brain_authority import BrainAuthorityPolicy, AuthorityLevel, require_authorized

class BrainAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.p=BrainAuthorityPolicy()

    def test_model_can_propose_but_not_execute(self):
        d=self.p.decide(subject="model",action="windows-real-boot",risk="LOW",capability=True)
        self.assertEqual(d.level, AuthorityLevel.PROPOSE)
        self.assertFalse(d.authorized)

    def test_capability_does_not_create_authority(self):
        d=self.p.decide(subject="windows-real-boot-qemu",action="windows-real-boot",risk="HIGH",capability=True)
        self.assertFalse(d.authorized)
        self.assertIn("HUMAN_APPROVAL",d.reason)

    def test_high_risk_denies_self_asserted_approval(self):
        d=self.p.decide(subject="windows-real-boot-qemu",action="windows-real-boot",risk="HIGH",capability=True,human_approval_token="true")
        self.assertFalse(d.authorized)

    def test_high_risk_accepts_verified_approval(self):
        import os
        os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"]="approval-secret"
        try:
            d=self.p.decide(subject="windows-real-boot-qemu",action="windows-real-boot",risk="HIGH",capability=True,human_approval_token="approval-secret")
            self.assertTrue(d.authorized)
        finally:
            os.environ.pop("BRAIN_HUMAN_APPROVAL_TOKEN",None)

    def test_critical_requires_approval(self):
        d=self.p.decide(subject="windows-real-boot-qemu",action="windows-real-boot",risk="CRITICAL",capability=True)
        self.assertFalse(d.authorized)

    def test_missing_capability_fails_closed(self):
        d=self.p.decide(subject="windows-real-boot-qemu",action="windows-real-boot",risk="LOW",capability=False)
        self.assertFalse(d.authorized)

    def test_invalid_risk_fails_closed(self):
        d=self.p.decide(subject="windows-real-boot-qemu",action="x",risk="UNKNOWN",capability=True)
        self.assertFalse(d.authorized)

    def test_root_self_assertion_is_denied(self):
        d=self.p.decide(subject="human-root",action="x",risk="CRITICAL",capability=False,root_authority_token="true")
        self.assertFalse(d.authorized)

    def test_root_requires_verified_token(self):
        import os
        os.environ["BRAIN_ROOT_AUTHORITY_TOKEN"]="root-secret"
        try:
            d=self.p.decide(subject="human-root",action="x",risk="CRITICAL",capability=False,root_authority_token="root-secret")
            self.assertTrue(d.authorized)
            self.assertEqual(d.level, AuthorityLevel.ROOT)
        finally:
            os.environ.pop("BRAIN_ROOT_AUTHORITY_TOKEN",None)

    def test_require_authorized(self):
        d=self.p.decide(subject="model",action="x",risk="LOW",capability=True)
        with self.assertRaises(PermissionError):
            require_authorized(d)

if __name__ == "__main__":
    unittest.main()
