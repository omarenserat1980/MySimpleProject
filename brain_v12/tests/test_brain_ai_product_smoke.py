"""End-to-end Brain product smoke: API -> memory -> agent -> verification -> evidence."""
import os
import tempfile
import unittest
from pathlib import Path

class BrainProductSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="brain-product-smoke-")
        root = Path(cls.tmp.name)
        os.environ.update({
            "BRAIN_DB": str(root / "brain.db"),
            "BRAIN_CHAT_DB": str(root / "brain_chat.db"),
            "BRAIN_EVIDENCE_DB": str(root / "evidence.db"),
            "BRAIN_GIT_ROOT": str(root / "brain_git"),
            "BRAIN_CONTROL_KEY": "product-smoke-control",
            "BRAIN_AGENT_KEY": "product-smoke-agent",
            "BRAIN_EMULATOR_KEY": "product-smoke-agent",
        })
        from fastapi.testclient import TestClient
        from brain_v12 import app as brain_app
        cls.app = brain_app
        cls.client = TestClient(brain_app.app)
        from brain_v12.brain.chat_identity import ChatIdentityStore
        identity_store = ChatIdentityStore(os.environ["BRAIN_CHAT_DB"])
        identity_store.init()
        credential = identity_store.issue("product-smoke-account", "product-smoke-device")
        cls.chat_headers = {"Authorization": "Bearer " + credential["token"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_product_path_produces_verified_evidence(self):
        control = {"X-Brain-Control-Key": "product-smoke-control"}
        agent = {"X-V12-Agent-Key": "product-smoke-agent"}

        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["ok"])

        ai = self.client.get("/api/brain-ai/status")
        self.assertEqual(ai.status_code, 200)
        self.assertTrue(ai.json()["ok"])
        self.assertTrue(ai.json()["memory_enabled"])
        self.assertTrue(ai.json()["tool_loop_enabled"])

        created = self.client.post("/api/brain-chat/sessions",
                                   json={"title": "Product Smoke"}, headers=self.chat_headers)
        self.assertEqual(created.status_code, 200)
        sid = created.json()["session"]["id"]

        saved = self.client.put(f"/api/brain-chat/sessions/{sid}/memory",
                                 json={"summary": "product-smoke-memory"}, headers=self.chat_headers)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["memory"]["summary"], "product-smoke-memory")

        memory = self.client.get(f"/api/brain-chat/sessions/{sid}/memory", headers=self.chat_headers)
        self.assertEqual(memory.status_code, 200)
        self.assertEqual(memory.json()["memory"]["summary"], "product-smoke-memory")

        queued = self.client.post("/api/device/enqueue", headers=control,
                                  json={"task": "python_version", "params": {}})
        self.assertEqual(queued.status_code, 200)
        task_id = queued.json()["task"]["task_id"]

        polled = self.client.get("/api/device/poll", headers=agent,
                                 params={"agent_id": "product-smoke-agent"})
        self.assertEqual(polled.status_code, 200)
        self.assertEqual(polled.json()["task"]["task_id"], task_id)

        report = self.client.post("/api/device/report", headers=agent, json={
            "task_id": task_id,
            "agent_id": "product-smoke-agent",
            "ok": True,
            "result": {"stdout": "Python product-smoke\\n", "returncode": 0},
            "error": "",
        })
        self.assertEqual(report.status_code, 200)

        result = self.client.get(f"/api/device/result/{task_id}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["task"]["status"], "COMPLETED")

        verified = self.app.device_bridge.verify_result(task_id)
        self.assertTrue(verified["verified"], verified)

        evidence = self.app.evidence_store.append(
            task_id,
            "product_smoke",
            {"task_id": task_id, "session_id": sid, "verification": verified,
             "proof": "completed_and_independently_verified"},
            "brain-product-smoke",
        )
        check = self.app.evidence_store.verify_hash(evidence["evidence_id"])
        self.assertTrue(check["ok"], check)

        fetched = self.client.get(f"/api/brain/evidence/{evidence['evidence_id']}")
        self.assertEqual(fetched.status_code, 200)
        body = fetched.json()
        self.assertEqual(body["verification_status"], "VERIFIED")
        self.assertEqual(body["payload"]["task_id"], task_id)
        self.assertEqual(body["payload"]["session_id"], sid)

if __name__ == "__main__":
    unittest.main()
