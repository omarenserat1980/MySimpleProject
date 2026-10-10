import unittest

from brain_v12.brain.apm_stage_discovery import from_mapping, from_sequence


class APMStageDiscoveryTests(unittest.TestCase):
    def test_declared_sequence_preserves_order(self):
        discovery = from_sequence(["A", "B", "C"])
        self.assertEqual(
            [stage.depends_on for stage in discovery.stages],
            [(), ("A",), ("B",)],
        )
        self.assertEqual(discovery.policy, "sequential")

    def test_independent_policy_is_explicit(self):
        discovery = from_sequence(["A", "B", "C"], policy="independent")
        self.assertEqual([stage.depends_on for stage in discovery.stages], [(), (), ()])

    def test_explicit_mapping_preserves_dependencies_and_resources(self):
        discovery = from_mapping([
            {"id": "A"},
            {"id": "B", "resource": "ffmpeg", "depends_on": ["A"]},
            {"id": "C", "depends_on": ["A"]},
        ])
        self.assertEqual(discovery.stages[1].resource, "ffmpeg")
        self.assertEqual(discovery.stages[1].depends_on, ("A",))
        self.assertEqual(discovery.stages[2].depends_on, ("A",))


if __name__ == "__main__":
    unittest.main()
