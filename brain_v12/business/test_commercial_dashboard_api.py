"""API tests for durable, authorization-gated commercial cases."""
import os
import tempfile
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from brain_v12.app import app


class CommercialDashboardAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        os.environ["BRAIN_COMMERCIAL_CASES_DB"] = os.path.join(cls.tempdir.name, "commercial.sqlite3")
        os.environ["BRAIN_CONTROL_KEY"] = "commercial-test-control-key"
        cls.client = TestClient(app, headers={"X-Brain-Control-Key": "commercial-test-control-key"})

    @classmethod
    def tearDownClass(cls):
        cls.tempdir.cleanup()
        os.environ.pop("BRAIN_COMMERCIAL_CASES_DB", None)
        os.environ.pop("BRAIN_CONTROL_KEY", None)

    def test_dashboard_endpoint(self):
        response = self.client.get("/api/commercial/dashboard")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["capabilities"], 5)
        self.assertTrue(payload["engineering_green_is_not_revenue"])

    def test_offers_endpoint_is_read_only(self):
        response = self.client.get("/api/commercial/offers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["offers"]), 5)

    def test_create_case_requires_control_key(self):
        response = TestClient(app).post(
            "/api/commercial/cases",
            json={"capability_id": "brain-automation-services", "case_id": "case-auth-test"},
        )
        self.assertEqual(response.status_code, 403)

    def test_create_case_is_durable_and_evidence_gated(self):
        case_id = f"case-{uuid4().hex[:10]}"
        response = self.client.post(
            "/api/commercial/cases",
            json={"capability_id": "brain-automation-services", "case_id": case_id},
        )
        self.assertEqual(response.status_code, 200)
        case = response.json()["case"]
        self.assertEqual(case["stage"], "OFFER_DEFINED")
        self.assertEqual(case["next_evidence_required"], "prospect_evidence")
        self.assertFalse(case["automatic_outreach"])
        self.assertFalse(case["automatic_contract"])
        self.assertFalse(case["automatic_charge"])
        self.assertFalse(case["automatic_withdrawal"])
        self.assertFalse(case["funds_moved_by_brain"])
        listed = self.client.get("/api/commercial/cases").json()["cases"]
        self.assertIn(case_id, [item["case_id"] for item in listed])

    def test_evidence_reference_does_not_advance_stage_or_verify_revenue(self):
        case_id = f"case-{uuid4().hex[:10]}"
        self.client.post(
            "/api/commercial/cases",
            json={"capability_id": "digital-commerce", "case_id": case_id},
        )
        response = self.client.post(
            f"/api/commercial/cases/{case_id}/evidence-references",
            json={"evidence_type": "payment", "evidence_ref": "receipt://example/123"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["evidence_reference_state"], "UNVERIFIED")
        self.assertFalse(payload["stage_advanced"])
        self.assertFalse(payload["revenue_verified"])
        self.assertEqual(payload["case"]["stage"], "OFFER_DEFINED")


if __name__ == "__main__":
    unittest.main()
