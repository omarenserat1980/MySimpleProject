import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from brain_v12.brain import windows_server_2025_simulation_api as api


class DummyRequest:
    def __init__(self, key=""):
        self.headers = {"X-Brain-Control-Key": key}


class WindowsServer2025SimulationApiTests(unittest.TestCase):
    def setUp(self):
        with api._LOCK:
            api._RUNS.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.state_patcher = patch.dict(
            os.environ, {"BRAIN_SIMULATION_STATE_DIR": self.tempdir.name}, clear=False
        )
        self.state_patcher.start()
        self.addCleanup(self.state_patcher.stop)
        os.environ.pop("BRAIN_CONTROL_KEY", None)

    def test_control_key_is_required(self):
        with self.assertRaises(HTTPException) as caught:
            api.create_simulation(api.SimulationRequest(), DummyRequest())
        self.assertEqual(caught.exception.status_code, 503)

    def test_wrong_control_key_is_rejected(self):
        with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": "expected"}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                api.create_simulation(api.SimulationRequest(), DummyRequest("wrong"))
        self.assertEqual(caught.exception.status_code, 403)

    def test_authorized_run_returns_synthetic_report_and_persists(self):
        with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": "expected"}, clear=False):
            response = api.create_simulation(
                api.SimulationRequest(scenario_id="success",
                                      hardware={"vcpu_count": 2, "ram_mib": 4096}),
                DummyRequest("expected"),
            )
            with api._LOCK:
                api._RUNS.clear()
            report = api.get_simulation_report(response["run_id"], DummyRequest("expected"))
        self.assertEqual(response["status"], "SIMULATED_BOOT_SUCCESS")
        self.assertFalse(response["real_windows_boot_verified"])
        self.assertEqual(report["execution_mode"], "SIMULATION_ONLY")
        self.assertFalse(report["real_windows_boot_verified"])
        self.assertTrue((Path(self.tempdir.name) / (response["run_id"] + ".json")).is_file())

    def test_unknown_hardware_field_is_rejected(self):
        with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": "expected"}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                api.create_simulation(
                    api.SimulationRequest(hardware={"connect_to_arkan": True}),
                    DummyRequest("expected"),
                )
        self.assertEqual(caught.exception.status_code, 422)

    def test_unknown_scenario_is_rejected(self):
        with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": "expected"}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                api.create_simulation(
                    api.SimulationRequest(scenario_id="real_boot"),
                    DummyRequest("expected"),
                )
        self.assertEqual(caught.exception.status_code, 422)

    def test_dashboard_route_is_registered_and_file_exists(self):
        paths = {route.path for route in api.router.routes}
        self.assertIn("/api/simulations/windows-server-2025/dashboard", paths)
        response = api.simulation_dashboard()
        self.assertTrue(Path(response.path).is_file())


if __name__ == "__main__":
    unittest.main()
