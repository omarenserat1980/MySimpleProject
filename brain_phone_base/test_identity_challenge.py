import base64
import unittest
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_phone_base.identity_challenge import (
    CHALLENGE_SCHEMA,
    RESPONSE_SCHEMA,
    VerificationError,
    canonical_json,
    public_key_id,
    sha256_hex,
    verify_challenge_response,
)


class IdentityChallengeTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc)
        self.verifier_private = Ed25519PrivateKey.generate()
        self.device_private = Ed25519PrivateKey.generate()
        self.verifier_public_pem = self.verifier_private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.device_public_pem = self.device_private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.measurement_hash = sha256_hex(b"fixture measurement")
        self.challenge = {
            "schema": CHALLENGE_SCHEMA,
            "challenge_id": "challenge-test-001",
            "nonce": "ab" * 32,
            "issued_at_utc": (self.now - timedelta(seconds=10)).isoformat().replace("+00:00", "Z"),
            "expires_at_utc": (self.now + timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
            "device_key_id": public_key_id(self.device_public_pem),
            "measurement_sha256": self.measurement_hash,
        }
        self.challenge_signature = base64.b64encode(
            self.verifier_private.sign(canonical_json(self.challenge))
        ).decode("ascii")
        self.response = {
            "schema": RESPONSE_SCHEMA,
            "challenge_id": self.challenge["challenge_id"],
            "nonce": self.challenge["nonce"],
            "device_key_id": self.challenge["device_key_id"],
            "measurement_sha256": self.measurement_hash,
            "signed_at_utc": self.now.isoformat().replace("+00:00", "Z"),
        }
        self.response_signature = base64.b64encode(
            self.device_private.sign(canonical_json(self.response))
        ).decode("ascii")

    def verify(self, **overrides):
        args = {
            "challenge": self.challenge,
            "challenge_signature_b64": self.challenge_signature,
            "pinned_verifier_public_key_pem": self.verifier_public_pem,
            "response": self.response,
            "response_signature_b64": self.response_signature,
            "enrolled_device_public_key_pem": self.device_public_pem,
            "expected_measurement_sha256": self.measurement_hash,
            "now": self.now,
        }
        args.update(overrides)
        return verify_challenge_response(**args)

    def test_valid_signatures_do_not_establish_identity_or_trust(self):
        result = self.verify(seen_challenge_ids=set())
        self.assertEqual(result["status"], "SIGNATURE_VALID_IDENTITY_UNVERIFIED")
        self.assertTrue(result["challenge_signature_valid"])
        self.assertTrue(result["device_response_signature_valid"])
        self.assertFalse(result["hardware_backed_key_verified"])
        self.assertFalse(result["android_key_attestation_verified"])
        self.assertFalse(result["device_identity_verified"])
        self.assertFalse(result["trusted"])
        self.assertFalse(result["active"])
        self.assertEqual(result["mining"], "DISABLED")

    def test_replayed_challenge_fails_closed(self):
        with self.assertRaisesRegex(VerificationError, "CHALLENGE_REPLAYED"):
            self.verify(seen_challenge_ids={self.challenge["challenge_id"]})

    def test_measurement_hash_mismatch_fails_closed(self):
        with self.assertRaisesRegex(VerificationError, "MEASUREMENT_HASH_MISMATCH"):
            self.verify(expected_measurement_sha256="0" * 64)

    def test_wrong_verifier_key_fails_signature(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with self.assertRaisesRegex(VerificationError, "SIGNATURE_INVALID"):
            self.verify(pinned_verifier_public_key_pem=other)

    def test_response_binding_mismatch_fails_closed(self):
        changed = dict(self.response)
        changed["nonce"] = "cd" * 32
        with self.assertRaisesRegex(VerificationError, "RESPONSE_BINDING_MISMATCH:nonce"):
            self.verify(response=changed)

    def test_expired_challenge_fails_closed(self):
        with self.assertRaisesRegex(VerificationError, "CHALLENGE_EXPIRED"):
            self.verify(now=self.now + timedelta(hours=1))


if __name__ == "__main__":
    unittest.main()
