"""Regression contract for the worker-registry HTTP authorization boundary."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "app.py"


def _function_for_route(tree, route):
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr in {"post", "put", "patch", "delete"} and decorator.args:
                    first = decorator.args[0]
                    if isinstance(first, ast.Constant) and first.value == route:
                        return node
    raise AssertionError(f"route not found: {route}")


def test_worker_registration_requires_control_auth_before_registry_mutation():
    tree = ast.parse(APP_SOURCE.read_text(encoding="utf-8"))
    endpoint = _function_for_route(tree, "/api/brain/workers/register")
    arguments = {arg.arg for arg in endpoint.args.args}
    assert "request" in arguments
    request_arg = next(arg for arg in endpoint.args.args if arg.arg == "request")
    assert isinstance(request_arg.annotation, ast.Name)
    assert request_arg.annotation.id == "Request"
    statements = endpoint.body
    auth_index = next(
        i for i, stmt in enumerate(statements)
        if isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Call)
        and isinstance(stmt.value.func, ast.Name)
        and stmt.value.func.id == "require_control_key"
    )
    mutation_index = next(
        i for i, stmt in enumerate(statements)
        if isinstance(stmt, ast.Return)
        and isinstance(stmt.value, ast.Call)
        and isinstance(stmt.value.func, ast.Attribute)
        and isinstance(stmt.value.func.value, ast.Name)
        and stmt.value.func.value.id == "worker_registry"
        and stmt.value.func.attr == "register"
    )
    assert auth_index < mutation_index
