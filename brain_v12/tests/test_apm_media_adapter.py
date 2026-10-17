import unittest

from brain_v12.brain.apm_media_adapter import build_media_apm_profile


class APMMediaAdapterTests(unittest.TestCase):
    def test_existing_media_dependencies_become_apm_graph(self):
        profile = build_media_apm_profile("test cinematic")
        stages = {stage.id: stage for stage in profile["stages"]}

        self.assertEqual(stages["IMAGE"].depends_on, ())
        self.assertEqual(stages["VOICE"].depends_on, ())
        self.assertEqual(stages["VIDEO"].depends_on, ("IMAGE", "VOICE"))
        self.assertEqual(stages["DESIGN"].depends_on, ("IMAGE", "VIDEO"))
        self.assertEqual(profile["parallelism"]["fan_out"], ["IMAGE", "VOICE"])

    def test_adapter_does_not_invent_resource_locks(self):
        profile = build_media_apm_profile("test cinematic")
        self.assertTrue(all(stage.resource is None for stage in profile["stages"]))


if __name__ == "__main__":
    unittest.main()
