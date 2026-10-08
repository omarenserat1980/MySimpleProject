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
