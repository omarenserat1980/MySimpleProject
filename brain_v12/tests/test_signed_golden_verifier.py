import base64
import tempfile
import time
import unittest
import uuid
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.signed_golden_verifier import (
    AUDIENCE, SCHEMA, signing_payload, verify_signed_verification,
)


class SignedGoldenVerifierTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.public = base64.b64encode(self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )).decode("ascii")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "evidence.db"
        self.now = time.time()
        self.expected = {
            "task_id": "task-1",
            "mission_id": "mission-1",
            "attempt": 2,
            "reality_level": "REAL",
            "verified": True,
            "evidence_ids": ["ev-a", "ev-b"],
            "criterion_ids": ["artifact-exists", "runtime-check"],
        }

    def signed(self, **overrides):
        document = {
            "schema": SCHEMA,
            "audience": AUDIENCE,
            "verifier_id": "verifier-01",
            **self.expected,
            "issued_at": self.now,
            "expires_at": self.now + 120,
            "nonce": uuid.uuid4().hex,
            **overrides,
        }
        document["signature"] = base64.b64encode(
            self.private.sign(signing_payload(document))
        ).decode("ascii")
        return document

    def verify(self, document, **kwargs):
        return verify_signed_verification(
            document, public_key_b64=self.public, now=self.now,
            replay_db_path=self.db, expected=self.expected, **kwargs,
        )

    def test_valid_signed_verification_is_accepted(self):
        result = self.verify(self.signed())
        self.assertTrue(result["verified"])
        self.assertEqual(result["verifier_id"], "verifier-01")

    def test_modified_scope_invalidates_signature_or_scope(self):
        document = self.signed()
        document["task_id"] = "different-task"
        with self.assertRaises(ValueError):
            self.verify(document)

    def test_wrong_scope_is_rejected_even_when_signed(self):
        document = self.signed(task_id="different-task")
        with self.assertRaisesRegex(ValueError, "SCOPE_MISMATCH:task_id"):
            self.verify(document)

    def test_expired_attestation_is_rejected(self):
        document = self.signed(issued_at=self.now - 400, expires_at=self.now - 1)
        with self.assertRaisesRegex(ValueError, "GOLDEN_VERIFIER_EXPIRED"):
            self.verify(document)

    def test_bad_trust_anchor_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "GOLDEN_VERIFIER_SIGNATURE_INVALID"):
            verify_signed_verification(
                self.signed(), public_key_b64=base64.b64encode(b"x" * 32).decode(),
                now=self.now, replay_db_path=self.db, expected=self.expected,
            )

    def test_nonce_replay_is_rejected(self):
        document = self.signed()
        self.verify(document)
        with self.assertRaisesRegex(ValueError, "GOLDEN_VERIFIER_REPLAY_DETECTED"):
            self.verify(document)

    def test_missing_trust_anchor_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "GOLDEN_VERIFIER_TRUST_KEY_REQUIRED"):
            verify_signed_verification(
                self.signed(), public_key_b64="", now=self.now,
                replay_db_path=self.db, expected=self.expected,
            )


    def test_boolean_attempt_cannot_match_integer_attempt(self):
        document = self.signed(attempt=True)
        with self.assertRaisesRegex(ValueError, "SCOPE_FIELD_INVALID:attempt"):
            self.verify(document)

    def test_scope_arrays_must_be_lists_of_strings(self):
        document = self.signed(evidence_ids="ev-a,ev-b")
        with self.assertRaisesRegex(ValueError, "SCOPE_FIELD_INVALID:evidence_ids"):
            self.verify(document)

    def test_non_finite_timestamp_is_rejected(self):
        document = self.signed()
        document["issued_at"] = float("nan")
        with self.assertRaisesRegex(ValueError, "GOLDEN_VERIFIER_TIME_INVALID"):
            self.verify(document)

    def test_clock_skew_cannot_extend_effective_validity_past_five_minutes(self):
        document = self.signed(
            issued_at=self.now + 50,
            expires_at=self.now + 340,
        )
        with self.assertRaisesRegex(ValueError, "GOLDEN_VERIFIER_VALIDITY_INVALID"):
            self.verify(document)

if __name__ == "__main__":
    unittest.main(verbosity=2)
