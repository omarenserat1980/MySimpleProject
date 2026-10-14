import unittest
from datetime import datetime, timedelta, timezone

from brain_v12.brain.proof_gate_engine import ProofGateEngine


NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
COMMIT = "a" * 40


def evidence(**overrides):
    item = {
        "evidence_id": "ev-1",
        "proof_type": "runtime_health",
        "source_type": "runtime_probe",
        "observed_at": NOW.isoformat(),
        "status": "VERIFIED",
        "environment": "production",
        "commit_sha": COMMIT,
        "artifact_sha256": "b" * 64,
    }
    item.update(overrides)
    return item


class ProofGateEngineTests(unittest.TestCase):
    def evaluate(self, records, **kwargs):
        return ProofGateEngine.evaluate(
            gate_id="runtime",
            required_proof_types=["runtime_health"],
            evidence_records=records,
            now=NOW,
            **kwargs,
        )

    def test_valid_revision_matched_evidence_passes(self):
        result = self.evaluate([evidence()], expected_commit_sha=COMMIT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["accepted_evidence_ids"], ["ev-1"])

    def test_missing_evidence_is_blocked(self):
        result = self.evaluate([])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "REQUIRED_EVIDENCE_MISSING")

    def test_stale_evidence_fails_closed(self):
        result = self.evaluate([evidence(observed_at=(NOW - timedelta(days=2)).isoformat())])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["rejected_evidence"][0]["reason"], "STALE_EVIDENCE")

    def test_synthetic_evidence_cannot_pass(self):
        result = self.evaluate([evidence(environment="fixture")])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["rejected_evidence"][0]["reason"], "SYNTHETIC_EVIDENCE")

    def test_commit_mismatch_fails_closed(self):
        result = self.evaluate([evidence(commit_sha="c" * 40)], expected_commit_sha=COMMIT)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["rejected_evidence"][0]["reason"], "COMMIT_MISMATCH")

    def test_disallowed_source_is_rejected(self):
        result = self.evaluate([evidence()], allowed_source_types=["pool_api"])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["rejected_evidence"][0]["reason"], "SOURCE_NOT_ALLOWED")

    def test_malformed_digest_is_rejected(self):
        result = self.evaluate([evidence(artifact_sha256="not-a-digest")])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["rejected_evidence"][0]["reason"], "INVALID_ARTIFACT_SHA256")

    def test_naive_timestamp_is_rejected(self):
        result = self.evaluate([evidence(observed_at="2026-10-14T12:00:00")])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["rejected_evidence"][0]["reason"], "INVALID_OBSERVED_AT")

    def test_non_pass_evidence_status_is_rejected(self):
        result = self.evaluate([evidence(status="NOT_RUN")])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["rejected_evidence"][0]["reason"], "EVIDENCE_NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
