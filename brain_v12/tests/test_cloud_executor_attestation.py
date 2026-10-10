import base64
import json
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.cloud_executor_attestation import (
    AUDIENCE, SCHEMA, signing_payload, verify_attestation,
)


class CloudExecutorAttestationTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key_b64 = base64.b64encode(
            self.private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode()
        self.now = 1_800_000_000
        self.document = {
            "schema": SCHEMA,
            "executor_id": "cloud-test-01",
            "audience": AUDIENCE,
            "issued_at": self.now - 5,
            "expires_at": self.now + 300,
            "nonce": "nonce-1234567890",
        }

    def write_signed(self, document=None):
        doc = dict(self.document if document is None else document)
        doc["signature"] = base64.b64encode(self.private_key.sign(signing_payload(doc))).decode()
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        json.dump(doc, handle)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def verify(self, path, **kwargs):
        return verify_attestation(
            path, self.public_key_b64, kwargs.pop("expected_executor_id", "cloud-test-01"),
            now=kwargs.pop("now", self.now), **kwargs
        )

    def test_accepts_valid_signed_attestation(self):
        result = self.verify(self.write_signed())
        self.assertTrue(result["verified"])
        self.assertEqual(result["executor_id"], "cloud-test-01")

    def test_rejects_modified_payload(self):
        path = self.write_signed()
        doc = json.loads(Path(path).read_text())
        doc["executor_id"] = "attacker"
        Path(path).write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "EXECUTOR_MISMATCH"):
            self.verify(path)

    def test_rejects_wrong_trust_key(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        path = self.write_signed()
        with self.assertRaisesRegex(ValueError, "SIGNATURE_INVALID"):
            verify_attestation(path, base64.b64encode(other).decode(), "cloud-test-01", now=self.now)

    def test_rejects_expired_attestation(self):
        doc = dict(self.document, expires_at=self.now - 1)
        with self.assertRaisesRegex(ValueError, "EXPIRED"):
            self.verify(self.write_signed(doc))

    def test_rejects_wrong_audience(self):
        doc = dict(self.document, audience="other-service")
        with self.assertRaisesRegex(ValueError, "AUDIENCE_MISMATCH"):
            self.verify(self.write_signed(doc))

    def test_rejects_overlong_validity(self):
        doc = dict(self.document, expires_at=self.now + 5000)
        with self.assertRaisesRegex(ValueError, "VALIDITY_INVALID"):
            self.verify(self.write_signed(doc))

    def test_rejects_missing_trust_key(self):
        with self.assertRaisesRegex(ValueError, "TRUST_KEY_REQUIRED"):
            verify_attestation(self.write_signed(), "", "cloud-test-01", now=self.now)


if __name__ == "__main__":
    unittest.main()
