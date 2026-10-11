"""Static safety contract tests for the simulation-first FastAPI routes."""
import ast
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"

class TestSimulationFirstRemoteAPIContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.routes = {}
        for node in cls.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and isinstance(dec.func.value, ast.Name) and dec.func.value.id == "app":
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            cls.routes[dec.args[0].value] = node

    def test_status_route_exists(self):
        self.assertIn("/api/remote-fabric/status", self.routes)

    def test_connect_route_requires_control_key_and_connects_gateway(self):
        fn = self.routes["/api/remote-fabric/connect"]
        src = ast.get_source_segment(self.source, fn)
        self.assertIn("require_control_key(request)", src)
        self.assertIn("arkan_remote_fabric.connect()", src)

    def test_simulation_command_is_controlled_and_size_bounded(self):
        fn = self.routes["/api/remote-fabric/simulation/command"]
        src = ast.get_source_segment(self.source, fn)
        self.assertIn("require_control_key(request)", src)
        self.assertIn("len(body.command) > 2000", src)
        self.assertIn('arkan_remote_fabric.mode != "VIRTUAL"', src)
        self.assertIn('"reality": "SIMULATED"', src)

    def test_real_promotion_is_explicit_and_audited(self):
        fn = self.routes["/api/remote-fabric/recover-real"]
        src = ast.get_source_segment(self.source, fn)
        self.assertIn("require_control_key(request)", src)
        self.assertIn("arkan_remote_fabric.recover_real()", src)
        self.assertIn("REMOTE_FABRIC_REAL_PROMOTION_ATTEMPT", src)

    def test_simulation_root_is_configurable_and_isolated(self):
        self.assertIn('BRAIN_ARKAN_SIM_ROOT', self.source)
        self.assertIn('".brain", "virtual", "arkan"', self.source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
