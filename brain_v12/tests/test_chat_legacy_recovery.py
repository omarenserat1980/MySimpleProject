import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.chat_legacy_recovery import (
    CONFIRM_PHRASE,
    apply_mapping,
    inventory,
)


class ChatLegacyRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "brain.db"
        with sqlite3.connect(self.db) as con:
            con.execute("""CREATE TABLE chat_sessions (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, account_id TEXT, device_id TEXT
            )""")
            con.executemany(
                "INSERT INTO chat_sessions VALUES(?,?,?,?,?,?)",
                [
                    ("legacy-1", "Legacy 1", "2026-01-01", "2026-01-01", None, "old-phone"),
                    ("legacy-2", "Legacy 2", "2026-01-02", "2026-01-02", "", None),
                    ("owned-1", "Owned", "2026-01-03", "2026-01-03", "account-a", "phone"),
                ],
            )

    def tearDown(self):
        self.tmp.cleanup()

    def test_inventory_is_read_only_and_excludes_message_content(self):
        before = sqlite3.connect(self.db).execute("SELECT id,account_id FROM chat_sessions ORDER BY id").fetchall()
        report = inventory(self.db)
        after = sqlite3.connect(self.db).execute("SELECT id,account_id FROM chat_sessions ORDER BY id").fetchall()
        self.assertEqual(before, after)
        self.assertEqual(report["unowned_count"], 2)
        self.assertNotIn("messages", json.dumps(report))
        self.assertEqual({row["id"] for row in report["unowned_sessions"]}, {"legacy-1", "legacy-2"})

    def test_apply_requires_explicit_confirmation(self):
        with self.assertRaisesRegex(ValueError, "EXPLICIT_CONFIRMATION_REQUIRED"):
            apply_mapping(self.db, {"legacy-1": "account-a"}, confirm="yes", actor="operator", reason="case-1")

    def test_apply_is_atomic_and_audited(self):
        result = apply_mapping(
            self.db,
            {"legacy-1": "account-a", "legacy-2": "account-b"},
            confirm=CONFIRM_PHRASE,
            actor="operator",
            reason="verified recovery case",
        )
        self.assertTrue(result["applied"])
        self.assertEqual(result["changed_count"], 2)
        with sqlite3.connect(self.db) as con:
            owners = dict(con.execute("SELECT id,account_id FROM chat_sessions"))
            audits = con.execute("SELECT session_id,assigned_account_id,actor,reason FROM chat_session_ownership_audit").fetchall()
        self.assertEqual(owners["legacy-1"], "account-a")
        self.assertEqual(owners["legacy-2"], "account-b")
        self.assertEqual(len(audits), 2)

    def test_refuses_unknown_or_already_owned_sessions_without_partial_changes(self):
        for mapping, expected in [
            ({"legacy-1": "account-a", "missing": "account-b"}, "UNKNOWN_SESSION_IDS"),
            ({"legacy-1": "account-a", "owned-1": "account-b"}, "SESSIONS_ALREADY_OWNED"),
        ]:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(ValueError, expected):
                    apply_mapping(self.db, mapping, confirm=CONFIRM_PHRASE, actor="operator", reason="test")
                with sqlite3.connect(self.db) as con:
                    owner = con.execute("SELECT account_id FROM chat_sessions WHERE id='legacy-1'").fetchone()[0]
                self.assertIsNone(owner)

    def test_requires_actor_and_reason(self):
        with self.assertRaisesRegex(ValueError, "ACTOR_AND_REASON_REQUIRED"):
            apply_mapping(self.db, {"legacy-1": "account-a"}, confirm=CONFIRM_PHRASE, actor="", reason="test")


if __name__ == "__main__":
    unittest.main()
