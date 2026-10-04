import unittest
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

    def test_event_has_unique_client_identity(self):
        a = ChatSyncEvent.new("session-1", "MESSAGE_ADDED", {"client_message_id": "a"}, "phone-01")
        b = ChatSyncEvent.new("session-1", "MESSAGE_ADDED", {"client_message_id": "b"}, "laptop-01")
        self.assertNotEqual(a.event_id, b.event_id)
        self.assertEqual(a.session_id, b.session_id)
        self.assertEqual(a.device_id, "phone-01")
        self.assertEqual(b.device_id, "laptop-01")


if __name__ == "__main__":
    unittest.main()
