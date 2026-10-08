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

    def test_high_risk_requires_approval(self):
        d=self.p.decide(subject="windows-real-boot-qemu",action="windows-real-boot",risk="HIGH",capability=True,human_approval=True)
        self.assertTrue(d.authorized)

    def test_critical_requires_approval(self):
        d=self.p.decide(subject="windows-real-boot-qemu",action="windows-real-boot",risk="CRITICAL",capability=True)
        self.assertFalse(d.authorized)

    def test_missing_capability_fails_closed(self):
        d=self.p.decide(subject="windows-real-boot-qemu",action="windows-real-boot",risk="LOW",capability=False)
        self.assertFalse(d.authorized)

    def test_invalid_risk_fails_closed(self):
        d=self.p.decide(subject="windows-real-boot-qemu",action="x",risk="UNKNOWN",capability=True)
        self.assertFalse(d.authorized)

    def test_root_is_explicit(self):
        d=self.p.decide(subject="human-root",action="x",risk="CRITICAL",capability=False,root_authority=True)
        self.assertTrue(d.authorized)
        self.assertEqual(d.level, AuthorityLevel.ROOT)

    def test_require_authorized(self):
        d=self.p.decide(subject="model",action="x",risk="LOW",capability=True)
        with self.assertRaises(PermissionError):
            require_authorized(d)

if __name__ == "__main__":
    unittest.main()
