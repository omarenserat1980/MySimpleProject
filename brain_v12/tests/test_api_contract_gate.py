"""API contract regression gate for critical Brain v12 control paths.

The gate focuses on stable externally observable contracts:
- canonical resilience paths remain ordered;
- health endpoints never claim healthy when a dependency is unhealthy;
- payment webhooks accept the repository's supported Pydantic runtime;
- authentication failures remain explicit.
"""
import os
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.api_resilience import router_factory
from brain_v12.brain.payment_gateway import router as payment_router


class _Device:
    def __init__(self, payload):
        self.payload = payload

    def agent_status(self):
        return self.payload


class ApiContractGateTests(unittest.TestCase):
    def test_resilience_paths_are_canonical(self):
        app = FastAPI()
        app.include_router(router_factory(_Device({"ok": True}), lambda: {"ok": True}))
        client = TestClient(app)

        response = client.get("/api/resilience/paths")
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertTrue(body["ok"])
        self.assertEqual(body["mode"], "CANONICAL_API_PATHS")
        self.assertIn("agent_status", body["dependencies"])
        self.assertIn("heartbeat_ttl", body["dependencies"]["agent_status"]["depends_on"])
        self.assertEqual(
            body["order"],
            [
                "runtime", "media", "agent_status", "agent_diagnostics",
                "queue", "device_status", "heartbeat", "poll", "report",
                "result", "verify",
            ],
        )

    def test_resilience_health_cannot_report_healthy_on_failed_runtime(self):
        app = FastAPI()
        app.include_router(
            router_factory(
                _Device({"ok": True}),
                lambda: {"ok": False, "status": "NOT_READY"},
            )
        )
        client = TestClient(app)

        response = client.get("/api/resilience/status")
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertFalse(body["ok"])
        self.assertFalse(body["healthy"])
        self.assertEqual(body["next"]["stage"], "runtime")
        self.assertEqual(body["next"]["path"], "/api/system/readiness")
        self.assertRegex(body["next"]["failure"]["failure_id"], r"^API-[A-F0-9]{16}$")

    def test_resilience_health_detects_offline_agent_status(self):
        app = FastAPI()
        app.include_router(
            router_factory(
                _Device({"online": False, "agents": []}),
                lambda: {"ok": True},
            )
        )
        client = TestClient(app)

        response = client.get("/api/resilience/status")
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertFalse(body["ok"])
        self.assertFalse(body["healthy"])
        self.assertEqual(body["next"]["stage"], "agent_status")
        self.assertEqual(body["next"]["path"], "/api/agent-gateway/status")
        self.assertRegex(body["next"]["failure"]["failure_id"], r"^API-[A-F0-9]{16}$")

    def test_resilience_health_cannot_report_healthy_on_failed_device(self):
        app = FastAPI()
        app.include_router(
            router_factory(
                _Device({"ok": False, "status": "DOWN"}),
                lambda: {"ok": True},
            )
        )
        client = TestClient(app)

        response = client.get("/api/resilience/status")
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertFalse(body["ok"])
        self.assertFalse(body["healthy"])
        self.assertEqual(body["next"]["stage"], "agent_status")
        self.assertEqual(body["next"]["path"], "/api/agent-gateway/status")

    def test_failure_identity_ignores_volatile_evidence(self):
        from brain_v12.brain.api_resilience import failure_identity

        first = failure_identity(
            "agent_status",
            "device_unhealthy",
            "heartbeat_ttl",
            {"ok": False, "online": False, "heartbeat_age": 2, "ts": 100},
        )
        second = failure_identity(
            "agent_status",
            "device_unhealthy",
            "heartbeat_ttl",
            {"ok": False, "online": False, "heartbeat_age": 14, "ts": 999},
        )

        self.assertEqual(first["failure_id"], second["failure_id"])
        self.assertEqual(first["identity_basis"], second["identity_basis"])

    def test_failure_identity_changes_for_different_root_state(self):
        from brain_v12.brain.api_resilience import failure_identity

        first = failure_identity("runtime", "runtime_unhealthy", "runtime", {"ok": False, "status": "DOWN"})
        second = failure_identity("runtime", "runtime_unhealthy", "runtime", {"ok": False, "status": "ERROR"})

        self.assertNotEqual(first["failure_id"], second["failure_id"])

    def test_payment_webhook_missing_secret_is_explicit_configuration_failure(self):
        old = os.environ.pop("BRAIN_PAYMENT_WEBHOOK_SECRET", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                app = FastAPI()
                app.include_router(payment_router(tmp + "/commerce.json"))
                response = TestClient(app).post(
                    "/api/payments/webhook",
                    content=b"{}",
                )
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["detail"], "PAYMENT_WEBHOOK_NOT_CONFIGURED")
        finally:
            if old is not None:
                os.environ["BRAIN_PAYMENT_WEBHOOK_SECRET"] = old


if __name__ == "__main__":
    unittest.main()
