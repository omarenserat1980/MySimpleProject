import base64
import tempfile
import time
import unittest
import uuid
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.brain.golden_acceptance_gate import (
    AcceptanceCriterion,
    GoldenAcceptanceGate,
)
from brain_v12.brain.signed_golden_verifier import (
    AUDIENCE as VERIFIER_AUDIENCE,
    SCHEMA as VERIFIER_SCHEMA,
    signing_payload,
)


class GoldenAcceptanceGateTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = EvidenceStore(Path(self.tempdir.name) / "evidence.db")
        self.gate = GoldenAcceptanceGate(self.store)
        self.criteria = (
            AcceptanceCriterion("artifact-exists", "artifact_verified"),
            AcceptanceCriterion("runtime-check", "runtime_check_passed"),
        )

    def tearDown(self):
        self.store.close()
        self.tempdir.cleanup()

    def _add_valid_bundle(self, *, reality="SIMULATED", verifier="independent-verifier"):
        first = self.store.append(
            "task-1", "artifact_verified",
            {"artifact": "artifact.bin", "reality_level": reality},
            producer="executor-A", mission_id="mission-1", attempt=2,
        )
        second = self.store.append(
            "task-1", "runtime_check_passed",
            {"checks_passed": 3, "reality_level": reality},
            producer="executor-A", mission_id="mission-1", attempt=2,
        )
        self.store.append(
            "task-1", "independent_verification",
            {
                "verified": True,
                "reality_level": reality,
                "verified_evidence_ids": [first["evidence_id"], second["evidence_id"]],
                "criterion_ids": ["artifact-exists", "runtime-check"],
            },
            producer=verifier, mission_id="mission-1", attempt=2,
        )
        return first, second

    def test_accepts_only_complete_hash_valid_same_attempt_bundle(self):
        first, second = self._add_valid_bundle()
        result = self.gate.evaluate(
            "task-1", self.criteria, mission_id="mission-1", attempt=2,
            expected_reality="SIMULATED",
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.status, "GOLDEN_LOOP_VERIFIED")
        self.assertEqual(set(result.evidence_ids), {first["evidence_id"], second["evidence_id"]})

    def test_missing_independent_verification_fails_closed(self):
        self.store.append(
            "task-1", "artifact_verified", {"reality_level": "SIMULATED"},
            producer="executor-A", mission_id="mission-1", attempt=2,
        )
        self.store.append(
            "task-1", "runtime_check_passed", {"reality_level": "SIMULATED"},
            producer="executor-A", mission_id="mission-1", attempt=2,
        )
        result = self.gate.evaluate("task-1", self.criteria, mission_id="mission-1", attempt=2)
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "INDEPENDENT_VERIFICATION_MISSING")

    def test_executor_cannot_verify_its_own_evidence(self):
        self._add_valid_bundle(verifier="executor-A")
        result = self.gate.evaluate("task-1", self.criteria, mission_id="mission-1", attempt=2)
        self.assertFalse(result.accepted)
        self.assertIn("INDEPENDENT_VERIFICATION_MISSING", result.reasons)

    def test_simulation_cannot_satisfy_real_execution_gate(self):
        self._add_valid_bundle(reality="SIMULATED")
        result = self.gate.evaluate(
            "task-1", self.criteria, mission_id="mission-1", attempt=2,
            expected_reality="REMOTE_EXECUTION_VERIFIED",
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "REALITY_LEVEL_MISMATCH")

    def test_evidence_from_another_attempt_is_not_accepted(self):
        self._add_valid_bundle()
        result = self.gate.evaluate("task-1", self.criteria, mission_id="mission-1", attempt=3)
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "INDEPENDENT_VERIFICATION_MISSING")
        self.assertTrue(any(reason.endswith("ACCEPTANCE_EVIDENCE_MISSING") for reason in result.reasons))

    def test_ci_evidence_does_not_satisfy_runtime_criterion(self):
        # CI must not satisfy a runtime criterion even if it labels the record
        # with the expected runtime evidence kind.
        self.store.append(
            "task-1", "artifact_verified", {"reality_level": "SIMULATED"},
            producer="github-actions", mission_id="mission-1", attempt=2,
        )
        self.store.append(
            "task-1", "runtime_check_passed", {"reality_level": "SIMULATED"},
            producer="github-actions", mission_id="mission-1", attempt=2,
        )
        result = self.gate.evaluate("task-1", self.criteria, mission_id="mission-1", attempt=2)
        self.assertFalse(result.accepted)
        self.assertTrue(any(reason.endswith("ACCEPTANCE_EVIDENCE_MISSING") for reason in result.reasons))

    def test_corrupted_payload_is_rejected(self):
        self._add_valid_bundle()
        first = self.store.for_task("task-1", mission_id="mission-1", attempt=2)[0]
        self.store.db.execute(
            "UPDATE evidence SET payload=? WHERE evidence_id=?",
            ('{"reality_level":"SIMULATED","tampered":true}', first["evidence_id"]),
        )
        self.store.db.commit()
        result = self.gate.evaluate("task-1", self.criteria, mission_id="mission-1", attempt=2)
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "EVIDENCE_INTEGRITY_FAILURE")

    def test_evidence_survives_store_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.db"
            store = EvidenceStore(path)
            first = store.append(
                "task-persist", "artifact_verified", {"reality_level": "SIMULATED"},
                producer="executor-A", mission_id="mission-persist", attempt=1,
            )
            second = store.append(
                "task-persist", "runtime_check_passed", {"reality_level": "SIMULATED"},
                producer="executor-A", mission_id="mission-persist", attempt=1,
            )
            store.append(
                "task-persist", "independent_verification",
                {
                    "verified": True, "reality_level": "SIMULATED",
                    "verified_evidence_ids": [first["evidence_id"], second["evidence_id"]],
                    "criterion_ids": ["artifact-exists", "runtime-check"],
                },
                producer="independent-verifier", mission_id="mission-persist", attempt=1,
            )
            store.close()

            reopened = EvidenceStore(path)
            try:
                result = GoldenAcceptanceGate(reopened).evaluate(
                    "task-persist", self.criteria, mission_id="mission-persist", attempt=1,
                )
                self.assertTrue(result.accepted)
                self.assertEqual(result.status, "GOLDEN_LOOP_VERIFIED")
            finally:
                reopened.close()

    def _add_signed_real_bundle(self):
        private_key = Ed25519PrivateKey.generate()
        public_key_b64 = base64.b64encode(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )).decode("ascii")
        first = self.store.append(
            "task-1", "artifact_verified",
            {"artifact": "artifact.bin", "reality_level": "REAL"},
            producer="executor-A", mission_id="mission-1", attempt=2,
        )
        second = self.store.append(
            "task-1", "runtime_check_passed",
            {"checks_passed": 3, "reality_level": "REAL"},
            producer="executor-A", mission_id="mission-1", attempt=2,
        )
        now = time.time()
        attestation = {
            "schema": VERIFIER_SCHEMA,
            "audience": VERIFIER_AUDIENCE,
            "verifier_id": "verifier-prod-01",
            "task_id": "task-1",
            "mission_id": "mission-1",
            "attempt": 2,
            "reality_level": "REAL",
            "verified": True,
            "evidence_ids": [first["evidence_id"], second["evidence_id"]],
            "criterion_ids": ["artifact-exists", "runtime-check"],
            "issued_at": now,
            "expires_at": now + 120,
            "nonce": uuid.uuid4().hex,
        }
        attestation["signature"] = base64.b64encode(
            private_key.sign(signing_payload(attestation))
        ).decode("ascii")
        self.store.append(
            "task-1", "independent_verification",
            {
                "verified": True,
                "reality_level": "REAL",
                "verified_evidence_ids": [first["evidence_id"], second["evidence_id"]],
                "criterion_ids": ["artifact-exists", "runtime-check"],
                "attestation": attestation,
            },
            producer="verifier-prod-01", mission_id="mission-1", attempt=2,
        )
        self.gate = GoldenAcceptanceGate(
            self.store, verifier_public_key_b64=public_key_b64
        )

    def test_real_acceptance_requires_valid_signed_verifier(self):
        self._add_signed_real_bundle()
        result = self.gate.evaluate(
            "task-1", self.criteria, mission_id="mission-1", attempt=2,
            expected_reality="REAL",
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.status, "GOLDEN_LOOP_VERIFIED")

    def test_real_acceptance_rejects_replayed_verifier_nonce(self):
        self._add_signed_real_bundle()
        first = self.gate.evaluate(
            "task-1", self.criteria, mission_id="mission-1", attempt=2,
            expected_reality="REAL",
        )
        second = self.gate.evaluate(
            "task-1", self.criteria, mission_id="mission-1", attempt=2,
            expected_reality="REAL",
        )
        self.assertTrue(first.accepted)
        self.assertFalse(second.accepted)
        self.assertTrue(any("GOLDEN_VERIFIER_REPLAY_DETECTED" in reason for reason in second.reasons))

    def test_real_acceptance_without_trust_anchor_fails_closed(self):
        self._add_signed_real_bundle()
        self.gate = GoldenAcceptanceGate(self.store)
        result = self.gate.evaluate(
            "task-1", self.criteria, mission_id="mission-1", attempt=2,
            expected_reality="REAL",
        )
        self.assertFalse(result.accepted)
        self.assertIn("SIGNED_INDEPENDENT_ATTESTATION_REQUIRED", result.reasons)

    def test_real_acceptance_requires_mission_and_attempt_scope(self):
        with self.assertRaisesRegex(ValueError, "REAL_ACCEPTANCE_MISSION_ID_REQUIRED"):
            self.gate.evaluate(
                "task-1", self.criteria, attempt=2, expected_reality="REAL",
            )
        with self.assertRaisesRegex(ValueError, "REAL_ACCEPTANCE_ATTEMPT_REQUIRED"):
            self.gate.evaluate(
                "task-1", self.criteria, mission_id="mission-1",
                expected_reality="REAL",
            )

    def test_empty_criteria_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "ACCEPTANCE_CRITERIA_REQUIRED"):
            self.gate.evaluate("task-1", [])

    def test_duplicate_criterion_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CRITERION_ID"):
            self.gate.evaluate("task-1", [
                AcceptanceCriterion("same", "a"),
                AcceptanceCriterion("same", "b"),
            ])


    def test_invalid_contract_types_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "EXPECTED_REALITY_INVALID"):
            self.gate.evaluate("task-1", self.criteria, expected_reality=7)
        with self.assertRaisesRegex(ValueError, "ACCEPTANCE_CRITERION_INVALID"):
            self.gate.evaluate("task-1", [object()])
        with self.assertRaisesRegex(ValueError, "ACCEPTANCE_CRITERIA_INVALID"):
            self.gate.evaluate("task-1", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
