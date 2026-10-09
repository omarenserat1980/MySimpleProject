import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.chat_request_ledger import ChatRequestLedger


class ChatRequestLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = ChatRequestLedger(Path(self.temp.name) / "brain.db")
        self.ledger.init()

    def tearDown(self):
        self.temp.cleanup()

    def test_duplicate_completed_request_replays_cached_response(self):
        self.assertEqual(self.ledger.claim("s1", "m1", "hash1")["status"], "CLAIMED")
        response = {"ok": True, "content": "answer"}
        self.ledger.complete("s1", "m1", response)
        replay = self.ledger.claim("s1", "m1", "hash1")
        self.assertEqual(replay, {"status": "COMPLETED", "response": response})

    def test_concurrent_duplicate_does_not_claim_twice(self):
        self.assertEqual(self.ledger.claim("s1", "m1", "hash1")["status"], "CLAIMED")
        self.assertEqual(self.ledger.claim("s1", "m1", "hash1")["status"], "IN_PROGRESS")

    def test_reusing_client_id_with_different_payload_is_rejected(self):
        self.ledger.claim("s1", "m1", "hash1")
        self.assertEqual(self.ledger.claim("s1", "m1", "different")["status"], "ID_CONFLICT")

    def test_failed_request_can_be_retried(self):
        self.ledger.claim("s1", "m1", "hash1")
        self.ledger.fail("s1", "m1")
        self.assertEqual(self.ledger.claim("s1", "m1", "hash1")["status"], "CLAIMED")


if __name__ == "__main__":
    unittest.main()
