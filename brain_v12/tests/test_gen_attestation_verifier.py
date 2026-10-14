import base64
import time
import unittest
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.gen_attestation_verifier import (
    AUDIENCE, SCHEMA, signing_payload, verify_gen_attestation,
    verify_gen_attestation_with_trust_store,
)


class GENAttestationVerifierTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.public = base64.b64encode(self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )).decode("ascii")
        self.now = time.time()
        self.nonce = uuid.uuid4().hex

    def signed(self, **overrides):
        doc = {
            "schema": SCHEMA,
            "audience": AUDIENCE,
            "issuer_id": "test-issuer",
            "subject_type": "HOSTED_ASIC",
            "subject_id": "hosted-asic-01",
            "evidence_id": "evidence-01",
            "operation": "read_only_diagnostic",
            "nonce": self.nonce,
            "result_digest": "a" * 64,
            "identity_verified": True,
            "physical_presence_verified": True,
            "network_connection_verified": True,
            "device_diagnostic_passed": True,
            "issued_at": self.now,
            "expires_at": self.now + 120,
            **overrides,
        }
        doc["signature"] = base64.b64encode(self.private.sign(signing_payload(doc))).decode("ascii")
        return doc

    def verify(self, doc, **kwargs):
        return verify_gen_attestation(
            doc, public_key_b64=self.public, expected_nonce=self.nonce,
            expected_issuer_id="test-issuer", expected_subject_id="hosted-asic-01", expected_subject_type="HOSTED_ASIC",
            expected_operation="read_only_diagnostic", now=self.now, **kwargs,
        )

    def test_trust_store_resolves_key_by_expected_issuer(self):
        result = verify_gen_attestation_with_trust_store(
            self.signed(), trusted_issuers={"test-issuer": self.public},
            expected_nonce=self.nonce, expected_issuer_id="test-issuer",
            expected_subject_id="hosted-asic-01", expected_subject_type="HOSTED_ASIC",
            expected_operation="read_only_diagnostic", now=self.now,
        )
        self.assertTrue(result["verified"])

    def test_unregistered_issuer_rejected_by_trust_store(self):
        with self.assertRaisesRegex(ValueError, "GEN_ISSUER_NOT_TRUSTED"):
            verify_gen_attestation_with_trust_store(
                self.signed(), trusted_issuers={"other-issuer": self.public},
                expected_nonce=self.nonce, expected_issuer_id="test-issuer",
                expected_subject_id="hosted-asic-01", expected_subject_type="HOSTED_ASIC",
                expected_operation="read_only_diagnostic", now=self.now,
            )

    def test_valid_signed_nonce_bound_attestation(self):
        result = self.verify(self.signed())
        self.assertTrue(result["verified"])
        self.assertEqual(result["subject_id"], "hosted-asic-01")

    def test_modified_payload_rejected(self):
        doc = self.signed()
        doc["result_digest"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "GEN_ATTESTATION_SIGNATURE_INVALID"):
            self.verify(doc)

    def test_wrong_fresh_nonce_rejected(self):
        with self.assertRaisesRegex(ValueError, "GEN_ATTESTATION_NONCE_MISMATCH"):
            self.verify(self.signed(nonce=uuid.uuid4().hex))

    def test_wrong_issuer_rejected(self):
        with self.assertRaisesRegex(ValueError, "GEN_ATTESTATION_ISSUER_MISMATCH"):
            self.verify(self.signed(issuer_id="attacker-controlled-issuer"))

    def test_wrong_subject_rejected(self):
        with self.assertRaisesRegex(ValueError, "GEN_ATTESTATION_SUBJECT_MISMATCH"):
            self.verify(self.signed(subject_id="different-device"))

    def test_expired_attestation_rejected(self):
        with self.assertRaisesRegex(ValueError, "GEN_ATTESTATION_EXPIRED"):
            self.verify(self.signed(issued_at=self.now - 400, expires_at=self.now - 1))

    def test_missing_trust_anchor_rejected(self):
        with self.assertRaisesRegex(ValueError, "GEN_TRUST_ANCHOR_REQUIRED"):
            verify_gen_attestation(
                self.signed(), public_key_b64="", expected_nonce=self.nonce,
                expected_issuer_id="test-issuer", expected_subject_id="hosted-asic-01", expected_subject_type="HOSTED_ASIC",
                expected_operation="read_only_diagnostic", now=self.now,
            )

    def test_failed_diagnostic_rejected(self):
        with self.assertRaisesRegex(ValueError, "GEN_ATTESTATION_CHECK_FAILED:device_diagnostic_passed"):
            self.verify(self.signed(device_diagnostic_passed=False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
