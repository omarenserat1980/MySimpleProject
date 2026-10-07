import unittest

from brain_v12.brain.chatgpt_device_gateway import ChatGPTDeviceGateway


class FakeBridge:
    def enqueue_chatgpt_ui(self, message, **kwargs):
        return {
            "ok": True,
            "status": "QUEUED",
            "task": {
                "task_id": "brain-termux-test",
                "task": "chatgpt_ui_send",
                "params": {
                    "approved": True,
                    "message": message,
                    **kwargs,
                },
            },
        }

    def verify_result(self, task_id):
        return {"ok": True, "verified": True, "status": "VERIFIED", "task_id": task_id}


class ChatGPTDeviceGatewayTests(unittest.TestCase):
    def test_contract_keeps_brain_authority(self):
        gateway = ChatGPTDeviceGateway(FakeBridge())
        contract = gateway.contract()
        self.assertEqual(contract["authority"], "BRAIN")
        self.assertEqual(contract["partner"], "CHATGPT")
        self.assertEqual(contract["executor"], "ANDROID_EXECUTOR")
        self.assertEqual(contract["task"], "chatgpt_ui_send")
        self.assertEqual(contract["target_package"], "com.openai.chatgpt")

    def test_send_requires_and_preserves_brain_decision_id(self):
        gateway = ChatGPTDeviceGateway(FakeBridge())
        result = gateway.send("افحص الحالة", decision_id="DEC-001")
        self.assertTrue(result["ok"])
        self.assertEqual(result["task"]["params"]["approved"], True)
        self.assertEqual(result["task"]["params"]["decision_id"], "DEC-001")


if __name__ == "__main__":
    unittest.main()
