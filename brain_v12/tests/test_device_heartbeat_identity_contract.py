"""Regression contract for explicit device identity in per-agent heartbeat mode."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "app.py"


def _function_for_route(tree, route):
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "post"
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
                and decorator.args[0].value == route
            ):
                return node
    raise AssertionError(f"route not found: {route}")


def test_heartbeat_rejects_missing_identity_when_per_agent_registry_is_configured():
    tree = ast.parse(APP_SOURCE.read_text(encoding="utf-8"))
    endpoint = _function_for_route(tree, "/api/device/heartbeat")
    source = ast.unparse(endpoint)
    assert 'os.getenv("BRAIN_AGENT_KEYS_JSON", "").strip()' in source
    assert 'detail="DEVICE_AGENT_ID_REQUIRED"' in source
    assert source.index("DEVICE_AGENT_ID_REQUIRED") < source.index("device_bridge.authenticate")
    assert 'agent_id = agent_id or "android-termux-v12"' in source
