#!/usr/bin/env python3
"""Regression tests for the short-lived Windows execution-contract fetcher.

All responses are mocked. These tests never contact the Control Plane or use secrets.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from brain_v12.brain import fetch_windows_execution_contract as fetcher

COMMIT = "a" * 40
RUN_ID = "123456789"
ATTEMPT = "github-123456789-attempt-1"


class FakeResponse:
    status = 200

    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def contract_payload(**overrides):
    contract = {
        "source_commit": COMMIT,
        "task_id": "windows-server-2025-real-boot",
        "attempt_id": ATTEMPT,
        "authority_signature": "fake-signature",
        "authority_signature_algorithm": "Ed25519",
        "expires_at": "4102444800",
    }
    contract.update(overrides)
    return {"issued": True, "contract": contract}


class FetchWindowsExecutionContractTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.destination = str(Path(self.tempdir.name) / "contract.json")
        self.env = {
            "BRAIN_WINDOWS_CONTROL_PLANE_URL": "https://control.example.invalid",
            "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY": "test-secret-never-log",
            "GITHUB_SHA": COMMIT,
            "GITHUB_RUN_ID": RUN_ID,
            "GITHUB_RUN_ATTEMPT": "1",
            "BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE": self.destination,
        }
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def run_main(self, payload=None, *, verifier=True):
        with (
            patch.dict(os.environ, self.env, clear=True),
            patch("urllib.request.urlopen", return_value=FakeResponse(payload or contract_payload())),
            patch("brain_v12.brain.authority_signature.verify_contract_signature", return_value=verifier),
            contextlib.redirect_stdout(self.stdout),
            contextlib.redirect_stderr(self.stderr),
        ):
            try:
                return fetcher.main()
            except RuntimeError as exc:
                print("BRAIN_CONTRACT_FETCH_FAILED=" + str(exc), file=self.stderr)
                return 2

    def test_valid_bound_signed_unexpired_contract_is_written_atomically(self):
        self.assertEqual(self.run_main(), 0)
        written = json.loads(Path(self.destination).read_text(encoding="utf-8"))
        self.assertEqual(written["source_commit"], COMMIT)
        self.assertEqual(written["task_id"], "windows-server-2025-real-boot")
        self.assertEqual(written["attempt_id"], ATTEMPT)
        self.assertEqual(Path(self.destination).stat().st_mode & 0o777, 0o600)
        self.assertIn("BRAIN_CONTRACT_FETCHED=1", self.stdout.getvalue())

    def test_commit_binding_mismatch_fails_closed_without_writing_contract(self):
        self.assertEqual(self.run_main(contract_payload(source_commit="b" * 40)), 2)
        self.assertFalse(Path(self.destination).exists())
        self.assertIn("BRAIN_CONTRACT_RESPONSE_BINDING_MISMATCH", self.stderr.getvalue())

    def test_invalid_signature_fails_closed_without_writing_contract(self):
        self.assertEqual(self.run_main(verifier=False), 2)
        self.assertFalse(Path(self.destination).exists())
        self.assertIn("BRAIN_CONTRACT_AUTHORITY_SIGNATURE_INVALID", self.stderr.getvalue())

    def test_delivery_key_is_never_echoed_on_failure(self):
        self.assertEqual(self.run_main(contract_payload(attempt_id="wrong-attempt")), 2)
        output = self.stdout.getvalue() + self.stderr.getvalue()
        self.assertNotIn("test-secret-never-log", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
