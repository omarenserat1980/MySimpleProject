import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.device_heartbeat_api import build_device_heartbeat_router


class FakeDeviceBridge:
    def __init__(self):
        self.keys = {
            "realme-01": "realme-test-key",
            "redmi3-01": "redmi-test-key",
            "android-termux-v12": "legacy-test-key",
        }
        self.heartbeats = []

    def authenticate(self, key, agent_id=None):
        if agent_id is None:
            return key == "legacy-test-key"
        return self.keys.get(agent_id) == key

    def heartbeat(self, agent_id, metadata):
        result = {"ok": True, "status": "HEARTBEAT", "agent_id": agent_id, "metadata": metadata}
        self.heartbeats.append(result)
        return result


class DeviceHeartbeatHttpTests(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeDeviceBridge()
        self.per_agent = True
        app = FastAPI()
        app.include_router(build_device_heartbeat_router(
            self.bridge, lambda: self.per_agent
        ))
        self.client = TestClient(app)

    def test_missing_identity_is_rejected_in_per_agent_mode(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Key": "realme-test-key"},
            json={"metadata": {"source": "unit-test"}},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "DEVICE_AGENT_ID_REQUIRED")
        self.assertEqual(self.bridge.heartbeats, [])

    def test_non_string_body_identity_is_rejected(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Key": "realme-test-key"},
            json={"agent_id": 123, "metadata": {"source": "unit-test"}},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "INVALID_DEVICE_AGENT_ID")
        self.assertEqual(self.bridge.heartbeats, [])

    def test_empty_list_metadata_is_rejected(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Id": "realme-01", "X-V12-Agent-Key": "realme-test-key"},
            json={"metadata": []},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "INVALID_DEVICE_METADATA")
        self.assertEqual(self.bridge.heartbeats, [])

    def test_null_metadata_is_rejected(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Id": "realme-01", "X-V12-Agent-Key": "realme-test-key"},
            json={"metadata": None},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "INVALID_DEVICE_METADATA")
        self.assertEqual(self.bridge.heartbeats, [])

    def test_non_object_metadata_is_rejected(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Id": "realme-01", "X-V12-Agent-Key": "realme-test-key"},
            json={"metadata": ["not", "an", "object"]},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "INVALID_DEVICE_METADATA")
        self.assertEqual(self.bridge.heartbeats, [])

    def test_missing_key_is_rejected_without_heartbeat(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Id": "realme-01"},
            json={"metadata": {"source": "unit-test"}},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "UNAUTHORIZED_AGENT")
        self.assertEqual(self.bridge.heartbeats, [])

    def test_wrong_device_key_is_rejected(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Id": "realme-01", "X-V12-Agent-Key": "redmi-test-key"},
            json={},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "UNAUTHORIZED_AGENT")
        self.assertEqual(self.bridge.heartbeats, [])

    def test_conflicting_header_and_body_identity_is_rejected(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Id": "realme-01", "X-V12-Agent-Key": "realme-test-key"},
            json={"agent_id": "redmi3-01"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "DEVICE_AGENT_ID_MISMATCH")
        self.assertEqual(self.bridge.heartbeats, [])

    def test_valid_body_identity_without_header(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Key": "realme-test-key"},
            json={"agent_id": "realme-01", "metadata": {"source": "unit-test"}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agent_id"], "realme-01")
        self.assertEqual(len(self.bridge.heartbeats), 1)

    def test_valid_per_agent_heartbeat_reaches_bridge(self):
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Id": "realme-01", "X-V12-Agent-Key": "realme-test-key"},
            json={"metadata": {"source": "unit-test"}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "HEARTBEAT")
        self.assertEqual(response.json()["agent_id"], "realme-01")
        self.assertEqual(len(self.bridge.heartbeats), 1)

    def test_legacy_default_identity_only_when_per_agent_mode_is_off(self):
        self.per_agent = False
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Key": "legacy-test-key"},
            json={"metadata": {"source": "legacy-test"}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agent_id"], "android-termux-v12")

    def test_wrong_legacy_key_is_rejected(self):
        self.per_agent = False
        response = self.client.post(
            "/api/device/heartbeat",
            headers={"X-V12-Agent-Key": "wrong-key"},
            json={},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "UNAUTHORIZED_AGENT")


if __name__ == "__main__":
    unittest.main()
