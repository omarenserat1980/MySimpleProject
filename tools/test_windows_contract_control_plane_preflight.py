#!/usr/bin/env python3
"""Synthetic tests for the read-only Control Plane issuance preflight."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from argparse import Namespace
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.owner_cryptographic_approval import approval_payload
from tools.windows_contract_control_plane_preflight import check

COMMIT = "a" * 40
TASK = "windows-server-2025-real-boot"
ATTEMPT = "github-123456789-attempt-1"


class ControlPlanePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.identity_path = root / "identity.json"
        self.checkpoint_path = root / "checkpoint.json"
        self.lease_path = root / "lease.json"
        self.approval_path = root / "approval.json"
        self.db_path = root / "leadership.db"
        self.private = Ed25519PrivateKey.generate()
        self.private_b64 = base64.b64encode(self.private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )).decode()
        self.public_b64 = base64.b64encode(self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )).decode()
        identity = {
            "schema": "brain.identity.v1", "brain_id": "brain-test",
            "source_commit": COMMIT, "checkpoint_id": "checkpoint-test", "generation": 7,
        }
        checkpoint = {
            "checkpoint_id": "checkpoint-test", "source_commit": COMMIT,
            "status": "STABLE_BASELINE",
        }
        now = time.time()
        lease = {
            "brain_id": "brain-test", "generation": 7, "lease_id": "lease-test",
            "fencing_token": 4, "holder_id": "control-plane-test",
            "acquired_at": now - 10, "expires_at": now + 600,
        }
        self.identity_path.write_text(json.dumps(identity))
        self.checkpoint_path.write_text(json.dumps(checkpoint))
        self.lease_path.write_text(json.dumps(lease))
        with sqlite3.connect(self.db_path) as db:
            db.execute("""CREATE TABLE leadership(
                singleton INTEGER PRIMARY KEY, brain_id TEXT, generation INTEGER,
                lease_id TEXT, fencing_token INTEGER, holder_id TEXT,
                acquired_at REAL, expires_at REAL)""")
            db.execute("""CREATE TABLE consumed_owner_approvals(
                challenge_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL, consumed_at REAL NOT NULL)""")
            db.execute("INSERT INTO leadership VALUES(1,?,?,?,?,?,?,?)", tuple(lease.values()))
        expires = now + 500
        fields = {
            "schema": "brain.owner-approval.v2", "owner_id": "owner-test",
            "challenge_id": "challenge-test", "scope": TASK, "expires_at": expires,
            "source_commit": COMMIT, "task_id": TASK, "attempt_id": ATTEMPT,
        }
        fields["signature"] = base64.b64encode(self.private.sign(approval_payload(
            fields["owner_id"], fields["challenge_id"], fields["scope"], fields["expires_at"],
            fields["source_commit"], fields["task_id"], fields["attempt_id"],
        ))).decode()
        self.approval_path.write_text(json.dumps(fields))
        self.args = Namespace(
            source_commit=COMMIT, task_id=TASK, attempt_id=ATTEMPT,
            identity_file=str(self.identity_path), checkpoint_file=str(self.checkpoint_path),
            lease_file=str(self.lease_path), owner_approval_file=str(self.approval_path),
            leadership_db=str(self.db_path),
        )
        self.env = {
            "BRAIN_AUTHORITY_PRIVATE_KEY_B64": self.private_b64,
            "BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64": self.public_b64,
            "BRAIN_HUMAN_APPROVAL_TOKEN": "synthetic-test-token",
        }

    def test_ready_report_does_not_issue_contract_or_consume_approval(self):
        with patch.dict(os.environ, self.env, clear=True):
            report = check(self.args)
        self.assertTrue(report["ok"], report)
        self.assertIn("LEADERSHIP_LEASE_CURRENT", report["passed"])
        self.assertIn("OWNER_APPROVAL_VALID_FOR_EXACT_ATTEMPT", report["passed"])
        self.assertFalse(report["contract_issued"])
        self.assertFalse(report["owner_approval_consumed"])
        self.assertFalse(report["system_state_changed"])

    def test_attempt_mismatch_fails_closed(self):
        self.args.attempt_id = "github-123456789-attempt-2"
        with patch.dict(os.environ, self.env, clear=True):
            report = check(self.args)
        self.assertFalse(report["ok"])
        self.assertIn("OWNER_APPROVAL_ATTEMPT_MISMATCH", report["blockers"])
        self.assertFalse(report["contract_issued"])

    def test_already_consumed_owner_approval_fails_closed(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO consumed_owner_approvals VALUES(?,?,?)",
                ("challenge-test", ATTEMPT, time.time()),
            )
        with patch.dict(os.environ, self.env, clear=True):
            report = check(self.args)
        self.assertFalse(report["ok"])
        self.assertIn("OWNER_APPROVAL_ALREADY_CONSUMED", report["blockers"])
        self.assertFalse(report["owner_approval_consumed"])

    def test_missing_private_key_fails_closed_without_echoing_values(self):
        env = dict(self.env)
        env.pop("BRAIN_AUTHORITY_PRIVATE_KEY_B64")
        with patch.dict(os.environ, env, clear=True):
            report = check(self.args)
        self.assertFalse(report["ok"])
        self.assertIn("BRAIN_AUTHORITY_PRIVATE_KEY_B64_REQUIRED", report["blockers"])
        self.assertNotIn(self.private_b64, json.dumps(report))


if __name__ == "__main__":
    unittest.main(verbosity=2)
