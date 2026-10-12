import unittest
import tempfile
from pathlib import Path

from brain_v12.brain.chat_session_store import ChatSessionStore
from brain_v12.brain.chat_sync import ChatSyncEvent, normalize_device_id, sync_contract


class ChatMultiDeviceSyncTests(unittest.TestCase):
    def test_contract_is_offline_first_and_idempotent(self):
        contract = sync_contract()
        self.assertTrue(contract["offline"])
        self.assertTrue(contract["idempotent"])
        self.assertEqual(contract["cursor"], "monotonic_server_event_id")

    def test_device_identity_is_required(self):
        self.assertEqual(normalize_device_id("phone-01"), "phone-01")
        with self.assertRaises(ValueError):
            normalize_device_id("")

    def test_shared_account_lists_sessions_across_devices(self):
        with tempfile.TemporaryDirectory() as td:
            store = ChatSessionStore(Path(td) / "chat.db")
            store.init()
            session = store.create("Shared", account_id="brain-account-1", device_id="phone-01")
            store.add_message(session["id"], "user", "hello", client_message_id="m-1", metadata={"device_id": "phone-01"})
            sessions = store.list(account_id="brain-account-1")
            self.assertEqual([s["id"] for s in sessions], [session["id"]])
            same = store.add_message(session["id"], "user", "hello", client_message_id="m-1", metadata={"device_id": "laptop-01"})
            self.assertEqual(len(same["messages"]), 1)
            self.assertEqual(same["messages"][0]["metadata"]["device_id"], "phone-01")

    def test_event_has_unique_client_identity(self):
        a = ChatSyncEvent.new("session-1", "MESSAGE_ADDED", {"client_message_id": "a"}, "phone-01")
        b = ChatSyncEvent.new("session-1", "MESSAGE_ADDED", {"client_message_id": "b"}, "laptop-01")
        self.assertNotEqual(a.event_id, b.event_id)
        self.assertEqual(a.session_id, b.session_id)
        self.assertEqual(a.device_id, "phone-01")
        self.assertEqual(b.device_id, "laptop-01")


if __name__ == "__main__":
    unittest.main()
