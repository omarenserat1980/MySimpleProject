import tempfile

# CI trigger: adaptive factory intelligence regression suite
import unittest
from pathlib import Path

from brain_v7.braincore_v2.audio_qc import evaluate_audio_evidence
from brain_v7.braincore_v2.research_gate import evaluate_research_gate
from brain_v7.braincore_v2.mastering_qc import evaluate_master
from brain_v7.braincore_v2.self_improvement import SelfImprovement
from brain_v7.braincore_v2.production_diagnostics import diagnose

class AdaptiveFactoryIntelligenceTests(unittest.TestCase):
    def test_audio_prompt_and_explicit_silence(self):
        shot = {"audio_mode": "silent", "quality_targets": {"audio_quality": .82}}
        result = evaluate_audio_evidence(shot, {})
        self.assertEqual(result["status"], "VERIFIED")

    def test_research_gate_blocks_unverified_claims(self):
        shot = {"genre": "scientific", "factuality": "factual"}
        ledger = {"claims": [{"claim": "x", "status": "UNVERIFIED"}]}
        self.assertEqual(evaluate_research_gate(shot, {}, ledger)["status"], "REPAIR")

    def test_research_gate_allows_verified_claims(self):
        shot = {"genre": "documentary", "factuality": "verified"}
        ledger = {"claims": [{"claim": "x", "status": "VERIFIED"}]}
        self.assertEqual(evaluate_research_gate(shot, {}, ledger)["status"], "VERIFIED")

    def test_self_improvement_requires_repeated_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            policy = SelfImprovement(Path(d) / "policy.json")
            for _ in range(2):
                policy.observe("shot", {"film_qc": {"checks": {"identity": False}}})
            self.assertTrue(any(r["dimension"] == "identity" for r in policy.context()["rules"]))

    def test_diagnostics_degraded_on_failed_qc(self):
        out = diagnose({"status": "SHOTS_BLOCKED", "visual_qc": {"status": "REJECTED"}})
        self.assertEqual(out["health"], "DEGRADED")

    def test_mastering_requires_video(self):
        self.assertEqual(evaluate_master(None, 12)["status"], "REPAIR")

if __name__ == "__main__":
    unittest.main()
