"""Prevent mining API routers from silently becoming unreachable."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "brain_v12" / "app.py"

MINING_ROUTER_MODULES = {
    "brain_v12.brain.mining_node_api": "mining_node_router",
    "brain_v12.brain.digital_mining_node_api": "digital_mining_node_router",
    "brain_v12.brain.bitcoin_mining_intelligence_api": "bitcoin_mining_intelligence_router",
    "brain_v12.brain.bitcoin_worker_api": "bitcoin_worker_router",
    "brain_v12.brain.asic_simulator_api": "asic_simulator_router",
}


def test_mining_api_routers_are_imported_and_mounted():
    tree = ast.parse(APP.read_text(encoding="utf-8"), filename=str(APP))
    imported = set()
    mounted = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if alias.name == "router":
                    imported.add((module, alias.asname))
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "include_router"
                and isinstance(func.value, ast.Name)
                and func.value.id == "app"
                and node.args
                and isinstance(node.args[0], ast.Name)
            ):
                mounted.add(node.args[0].id)

    missing_imports = {
        module: alias
        for module, alias in MINING_ROUTER_MODULES.items()
        if (module.removeprefix("brain_v12.").replace("brain_v12.", ""), alias) not in imported
        and (module.replace("brain_v12.", ""), alias) not in imported
    }
    missing_mounts = {
        alias for alias in MINING_ROUTER_MODULES.values() if alias not in mounted
    }

    assert not missing_imports, f"Mining router imports missing or renamed: {missing_imports}"
    assert not missing_mounts, f"Mining routers not mounted on FastAPI app: {sorted(missing_mounts)}"
