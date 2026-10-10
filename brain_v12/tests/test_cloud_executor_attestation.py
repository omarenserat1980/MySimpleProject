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
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.replay_db = str(Path(self.tmp.name) / 'used-nonces.sqlite3')
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
        path = Path(self.tmp.name) / f'attestation-{len(list(Path(self.tmp.name).glob("attestation-*.json")))}.json'
        path.write_text(json.dumps(doc), encoding='utf-8')
        return str(path)

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
        doc["nonce"] = "nonce-abcdefghijklmnop"
        Path(path).write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "SIGNATURE_INVALID"):
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

    def test_rejects_reuse_of_consumed_nonce(self):
        path = self.write_signed()
        self.verify(path, replay_db_path=self.replay_db)
        with self.assertRaisesRegex(ValueError, "REPLAY_DETECTED"):
            self.verify(path, replay_db_path=self.replay_db)

    def test_replay_ledger_is_shared_across_attestation_files(self):
        first = self.write_signed()
        second = self.write_signed()
        self.verify(first, replay_db_path=self.replay_db)
        with self.assertRaisesRegex(ValueError, "REPLAY_DETECTED"):
            self.verify(second, replay_db_path=self.replay_db)

    def test_rejects_replay_store_symlink(self):
        real_db = str(Path(self.tmp.name) / "real.sqlite3")
        self.verify(self.write_signed(), replay_db_path=real_db)
        link = str(Path(self.tmp.name) / "link.sqlite3")
        Path(link).symlink_to(real_db)
        fresh = dict(self.document, nonce="nonce-abcdefghijklmnop")
        with self.assertRaisesRegex(ValueError, "SYMLINK_REJECTED"):
            self.verify(self.write_signed(fresh), replay_db_path=link)


if __name__ == "__main__":
    unittest.main()
