import base64
import json
import time
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.cloud_executor_gate import (
    ATTESTATION_SCHEMA,
    _canonical_attestation_payload,
    _verify_attestation,
)


class CloudExecutorAttestationTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_b64 = base64.b64encode(public).decode("ascii")
        self.now = int(time.time())
        self.expected = {
            "schema": ATTESTATION_SCHEMA,
            "executor_id": "runner-ark-01",
            "hostname": "brain-runner-01",
            "architecture": "x86_64",
            "issued_at": self.now - 5,
            "expires_at": self.now + 300,
        }

    def signed(self, **changes):
        attestation = dict(self.expected)
        attestation.update(changes)
        attestation["signature"] = base64.b64encode(
            self.private.sign(_canonical_attestation_payload(attestation))
        ).decode("ascii")
        return json.dumps(attestation)

    def verify(self, raw, key=None, **expected):
        values = {
            "expected_executor_id": "runner-ark-01",
            "expected_hostname": "brain-runner-01",
            "expected_architecture": "x86_64",
            "now": self.now,
        }
        values.update(expected)
        return _verify_attestation(raw, self.public_b64 if key is None else key, **values)

    def test_accepts_valid_short_lived_signed_attestation(self):
        ok, reason = self.verify(self.signed())
        self.assertTrue(ok, reason)

    def test_rejects_missing_attestation_or_trust_root(self):
        self.assertFalse(self.verify("")[0])
        self.assertFalse(self.verify(self.signed(), key="")[0])

    def test_rejects_tampered_signed_fields(self):
        attestation = json.loads(self.signed())
        attestation["executor_id"] = "other-runner"
        ok, reason = self.verify(json.dumps(attestation))
        self.assertFalse(ok)
        self.assertEqual(reason, "attestation-executor_id-mismatch")

    def test_rejects_wrong_hostname_binding(self):
        ok, reason = self.verify(self.signed(), expected_hostname="different-host")
        self.assertFalse(ok)
        self.assertEqual(reason, "attestation-hostname-mismatch")

    def test_rejects_expired_attestation(self):
        raw = self.signed(issued_at=self.now - 500, expires_at=self.now - 1)
        ok, reason = self.verify(raw)
        self.assertFalse(ok)
        self.assertEqual(reason, "attestation-expired")

    def test_rejects_excessive_lifetime(self):
        raw = self.signed(issued_at=self.now - 1, expires_at=self.now + 3600)
        ok, reason = self.verify(raw)
        self.assertFalse(ok)
        self.assertEqual(reason, "attestation-lifetime-invalid")

    def test_rejects_invalid_signature(self):
        other = Ed25519PrivateKey.generate()
        attestation = dict(self.expected)
        attestation["signature"] = base64.b64encode(
            other.sign(_canonical_attestation_payload(attestation))
        ).decode("ascii")
        ok, reason = self.verify(json.dumps(attestation))
        self.assertFalse(ok)
        self.assertEqual(reason, "attestation-signature-invalid")


if __name__ == "__main__":
    unittest.main()
