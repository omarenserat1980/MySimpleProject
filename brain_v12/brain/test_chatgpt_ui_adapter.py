import unittest
from brain_v12.brain.chatgpt_ui_adapter import HumanChatGPTUI


class FakeUI:
    def __init__(self, click=True, ready=True, response="رد ChatGPT"):
        self.click = click
        self.ready = ready
        self.response = response
        self.calls = []

    def type_message(self, message):
        self.calls.append(("type", message))
        return {"ok": True}

    def click_send(self):
        self.calls.append(("click",))
        return {"ok": self.click, "clicked": self.click}

    def wait_for_response(self, timeout=120.0):
        self.calls.append(("wait", timeout))
        return {"ok": self.ready, "ready": self.ready}

    def read_response(self):
        self.calls.append(("read",))
        return {"ok": bool(self.response), "text": self.response}


class ChatGPTUIAdapterTests(unittest.TestCase):
    def test_full_human_flow_is_verified(self):
        fake = FakeUI()
        result = HumanChatGPTUI(fake).send("اسأل ChatGPT")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "UI_CONVERSATION_VERIFIED")
        self.assertTrue(result["ui_clicked"])
        self.assertEqual(result["evidence"]["response_text"], "رد ChatGPT")
        self.assertEqual([x[0] for x in fake.calls], ["type", "click", "wait", "read"])

    def test_click_must_be_verified(self):
        result = HumanChatGPTUI(FakeUI(click=False)).send("رسالة")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "SEND_CLICK_NOT_VERIFIED")
        self.assertFalse(result["ui_clicked"])

    def test_response_must_be_read(self):
        result = HumanChatGPTUI(FakeUI(response="")).send("رسالة")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "RESPONSE_READ_FAILED")

    def test_missing_adapter_fails_closed(self):
        result = HumanChatGPTUI().send("رسالة")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UI_ADAPTER_NOT_CONFIGURED")


if __name__ == "__main__":
    unittest.main()
