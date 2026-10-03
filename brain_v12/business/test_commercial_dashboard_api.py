"""API tests for commercial operations and evidence-gated cases."""
import unittest

from fastapi.testclient import TestClient

from brain_v12.app import app


class CommercialDashboardAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_dashboard_endpoint(self):
        response = self.client.get("/api/commercial/dashboard")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["capabilities"], 5)
        self.assertEqual(payload["verified_revenue"], 0.0)
        self.assertEqual(payload["verified_profit"], 0.0)
        self.assertTrue(payload["engineering_green_is_not_revenue"])

    def test_offers_endpoint_is_read_only(self):
        response = self.client.get("/api/commercial/offers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["offers"]), 5)

    def test_create_case_is_evidence_gated(self):
        response = self.client.post(
            "/api/commercial/cases",
            json={"capability_id": "brain-automation-services", "case_id": "case-create-test"},
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

    def test_cases_endpoint_lists_created_case(self):
        created = self.client.post(
            "/api/commercial/cases",
            json={"capability_id": "digital-commerce", "case_id": "case-list-test"},
        )
        self.assertEqual(created.status_code, 200)
        response = self.client.get("/api/commercial/cases")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertGreaterEqual(len(response.json()["cases"]), 1)


if __name__ == "__main__":
    unittest.main()
