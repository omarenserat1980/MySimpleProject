import json
import os
import sqlite3
import tempfile
import time
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from tools.windows_contract_control_plane_preflight import check


class ReplayLedgerTests(unittest.TestCase):
    def test_consumed_challenge_is_rejected_without_mutating_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db_path = root / "leadership.db"
            now = time.time()
            lease = {
                "brain_id": "brain-test", "generation": 1, "lease_id": "lease-test",
                "fencing_token": 1, "holder_id": "holder-test", "acquired_at": now - 1,
                "expires_at": now + 600,
            }
            with sqlite3.connect(db_path) as db:
                db.execute("CREATE TABLE leadership (singleton INTEGER PRIMARY KEY, brain_id TEXT, generation INTEGER, lease_id TEXT, fencing_token INTEGER, holder_id TEXT, acquired_at REAL, expires_at REAL)")
                db.execute("INSERT INTO leadership VALUES (1,?,?,?,?,?,?,?)", tuple(lease.values()))
                db.execute("CREATE TABLE consumed_owner_approvals (challenge_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL, consumed_at REAL NOT NULL)")
                db.execute("INSERT INTO consumed_owner_approvals VALUES ('challenge-test','github-123-attempt-1',?)", (now,))
            identity = root / "identity.json"
            checkpoint = root / "checkpoint.json"
            lease_file = root / "lease.json"
            approval_file = root / "approval.json"
            for path, value in ((identity, {}), (checkpoint, {}), (lease_file, lease), (approval_file, {"challenge_id": "challenge-test"})):
                path.write_text(json.dumps(value), encoding="utf-8")
            args = Namespace(
                source_commit="a" * 40, task_id="windows-server-2025-real-boot",
                attempt_id="github-123-attempt-1", identity_file=str(identity),
                checkpoint_file=str(checkpoint), lease_file=str(lease_file),
                owner_approval_file=str(approval_file), leadership_db=str(db_path),
            )
            env = {
                "BRAIN_AUTHORITY_PRIVATE_KEY_B64": "A" * 44,
                "BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64": "A" * 44,
                "BRAIN_HUMAN_APPROVAL_TOKEN": "synthetic",
            }
            # This is a narrow regression of the ledger branch. Earlier identity
            # and signature checks are mocked so the test uses no real authority.
            class SyntheticOwner:
                challenge_id = "challenge-test"
                scope = "windows-server-2025-real-boot"
                expires_at = now + 500
            with patch.dict(os.environ, env, clear=True), \
                 patch("brain_v12.brain.brain_identity.require_checkpoint_identity"), \
                 patch("brain_v12.brain.owner_cryptographic_approval.verify_owner_approval", return_value=SyntheticOwner()):
                report = check(args)
            self.assertFalse(report["ok"])
            self.assertIn("OWNER_APPROVAL_ALREADY_CONSUMED", report["blockers"])
            with sqlite3.connect(db_path) as db:
                row = db.execute("SELECT challenge_id, attempt_id FROM consumed_owner_approvals").fetchone()
            self.assertEqual(row, ("challenge-test", "github-123-attempt-1"))
            self.assertFalse(report["owner_approval_consumed"])


if __name__ == "__main__":
    unittest.main()
