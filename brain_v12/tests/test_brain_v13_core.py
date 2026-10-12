import unittest

from brain_v12.brain.brain_constitution import BrainConstitution, ConstitutionViolation
from brain_v12.brain.execution_contract import ExecutionContract
from brain_v12.brain.mission import Mission, MissionState
from brain_v12.brain.reality_core import KnowledgeKind, Observation, RealityCore
from brain_v12.brain.uncertainty import UncertaintyEngine


class BrainV13CoreTests(unittest.TestCase):
    def test_mission_happy_path(self):
        m = Mission("m1", "connect android", max_attempts=2)
        for state in (
            MissionState.UNDERSTANDING, MissionState.PLANNING,
            MissionState.READY, MissionState.EXECUTING,
            MissionState.OBSERVING, MissionState.VERIFYING,
            MissionState.COMPLETED,
        ):
            m.transition(state, reason="test")
        self.assertEqual(m.state, MissionState.COMPLETED)
        self.assertEqual(m.attempts, 1)
        self.assertEqual(m.metadata["transition_reasons"][0]["from"], "CREATED")

    def test_mission_blocks_unbounded_retry(self):
        m = Mission("m2", "test", max_attempts=1)
        m.transition(MissionState.UNDERSTANDING)
        m.transition(MissionState.PLANNING)
        m.transition(MissionState.READY)
        m.transition(MissionState.EXECUTING)
        m.transition(MissionState.DIAGNOSING)
        m.transition(MissionState.RECOVERING)
        with self.assertRaises(ValueError):
            m.transition(MissionState.RETEST)

    def test_reality_detects_contradiction(self):
        r = RealityCore()
        r.observe(Observation("android.runtime", "RUNNING", source="agent"))
        r.observe(Observation("android.runtime", "DOWN", source="api"))
        resolved = r.resolve("android.runtime")
        self.assertEqual(resolved.kind, KnowledgeKind.CONTRADICTED)
        self.assertIn("android.runtime", r.contradictions())

    def test_uncertainty(self):
        e = UncertaintyEngine()
        self.assertEqual(e.classify(evidence_count=0).status, "UNKNOWN")
        self.assertEqual(e.classify(evidence_count=1, confidence=.95).status, "KNOWN")
        self.assertEqual(e.classify(evidence_count=1, confidence=.7).status, "LIKELY")
        self.assertEqual(e.classify(evidence_count=1, confidence=.2).status, "UNCERTAIN")

    def test_contract_and_constitution(self):
        c = ExecutionContract("m", "t", "ping", "android", risk="HIGH")
        c.validate()
        with self.assertRaises(ConstitutionViolation):
            BrainConstitution().assert_external(risk="HIGH", approved=False)
        with self.assertRaises(ConstitutionViolation):
            BrainConstitution().assert_success_claim(verified=True, evidence_ids=[])


if __name__ == "__main__":
    unittest.main()
