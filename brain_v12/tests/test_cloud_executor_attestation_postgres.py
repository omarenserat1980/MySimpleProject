"""Opt-in PostgreSQL integration test for the cloud-executor registry.

Set BRAIN_TEST_POSTGRES_URL to a disposable test database URL to run this test.
It is skipped in normal CI unless that explicit test database is configured.
"""
import base64
import hashlib
import json
import os
import unittest
import uuid
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException

from brain_v12.brain.cloud_executor_attestation_api import (
    ConsumeRequest,
    ExecutorRequest,
    IssueRequest,
    attestation_challenge,
    attestation_consume,
    attestation_issue,
)


@unittest.skipUnless(os.environ.get("BRAIN_TEST_POSTGRES_URL"), "BRAIN_TEST_POSTGRES_URL not configured")
class CloudExecutorPostgresRegistryTests(unittest.TestCase):
    def test_challenge_issue_consume_and_replay_rejection(self):
        executor_id = "pg-test-" + uuid.uuid4().hex
        token = uuid.uuid4().hex + uuid.uuid4().hex
        private = Ed25519PrivateKey.generate()
        private_b64 = base64.b64encode(private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )).decode("ascii")
        env = {
            "BRAIN_CLOUD_EXECUTOR_REGISTRY_DB": os.environ["BRAIN_TEST_POSTGRES_URL"],
            "BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON": json.dumps({
                executor_id: hashlib.sha256(token.encode()).hexdigest()
            }),
            "BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64": private_b64,
            "BRAIN_CLOUD_EXECUTOR_HOST_BINDINGS_JSON": json.dumps({
                executor_id: {"hostname": "integration-test-host", "architecture": "x86_64"}
            }),
        }
        with patch.dict("os.environ", env):
            challenge = attestation_challenge(ExecutorRequest(executor_id=executor_id), token)
            attestation = attestation_issue(
                IssueRequest(executor_id=executor_id, nonce=challenge["nonce"]), token
            )
            first = attestation_consume(
                ConsumeRequest(executor_id=executor_id, nonce=attestation["nonce"]), token
            )
            self.assertTrue(first["consumed"])
            with self.assertRaises(HTTPException) as raised:
                attestation_consume(
                    ConsumeRequest(executor_id=executor_id, nonce=attestation["nonce"]), token
                )
            self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
