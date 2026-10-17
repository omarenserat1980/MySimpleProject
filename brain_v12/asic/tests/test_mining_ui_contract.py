"""Regression checks for the Brain SHA-256d UI's honest evidence contract.

These checks inspect source wiring only. They do not claim the live API is reachable
or that an RTL simulation ran in a deployed Brain instance.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
UI = ROOT / "brain_v12" / "web" / "brain.html"
API = ROOT / "brain_v12" / "brain" / "asic_simulator_api.py"
APP = ROOT / "brain_v12" / "app.py"


class MiningUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = UI.read_text(encoding="utf-8")
        cls.api = API.read_text(encoding="utf-8")
        cls.app = APP.read_text(encoding="utf-8")

    def test_ui_calls_registered_simulator_status_endpoint(self):
        self.assertIn("fetch('/api/asic-sim/status')", self.ui)
        self.assertIn("app.include_router(asic_simulator_router)", self.app)
        self.assertIn('@router.get("/status")', self.api)

    def test_ui_rtl_action_uses_real_rtl_endpoint_not_software_fallback(self):
        self.assertIn("fetch(u,o)", self.ui)
        self.assertIn("'/api/asic-sim/sha256d-rtl-self-test'", self.ui)
        self.assertIn('@router.post("/sha256d-rtl-self-test")', self.api)
        self.assertIn("adapter.simulate_sha256d_rtl", self.api)

    def test_success_claim_requires_explicit_verified_response(self):
        self.assertIn(
            "r.status==='RTL_SIMULATION_VERIFIED'&&r.ok===true", self.ui
        )
        self.assertIn('"physical_asic_executed":False', self.api)
        self.assertIn('"hardware_access": False', self.api)
        self.assertIn('"network_access": False', self.api)

    def test_unwired_runtime_is_not_reported_as_success(self):
        self.assertIn("BRAIN_ASIC_RUNTIME_NOT_WIRED", self.api)
        self.assertIn("لا يُعد فشل الاتصال نجاحًا", self.ui)

    def test_ui_labels_physical_asic_and_pool_as_unverified(self):
        self.assertIn("ASIC مادي / Pool", self.ui)
        self.assertIn("غير مثبت", self.ui)
        self.assertIn("لا تُحوّل نتائج المحاكاة إلى تعدين حي", self.ui)


if __name__ == "__main__":
    unittest.main()
