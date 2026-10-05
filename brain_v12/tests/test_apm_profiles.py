import unittest

from brain_v12.brain.apm_profiles import cognitive_v12_profile, readiness_profile


class APMProfileTests(unittest.TestCase):
    def test_cognitive_profile_preserves_sequence(self):
        profile = cognitive_v12_profile()
        self.assertEqual(profile.policy, "sequential")
        self.assertEqual(profile.stages[0].id, "PERCEIVE")
        self.assertEqual(profile.stages[-1].id, "LEARN")
        self.assertEqual(profile.stages[1].depends_on, ("PERCEIVE",))

    def test_readiness_profile_declares_dependencies(self):
        stages = {s.id: s for s in readiness_profile().stages}
        self.assertEqual(stages["S3"].depends_on, ("S2",))
        self.assertEqual(stages["S4"].depends_on, ("S2",))
        self.assertEqual(stages["S5"].depends_on, ("S1",))
        self.assertEqual(stages["S8"].depends_on, ("S1",))
        self.assertEqual(stages["S10"].depends_on, ("S1",))
        self.assertEqual(stages["S6"].depends_on, ("S4", "S5"))


if __name__ == "__main__":
    unittest.main()
