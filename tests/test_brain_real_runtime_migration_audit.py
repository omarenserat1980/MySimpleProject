from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.brain_real_runtime_migration_audit import build_report


def test_source_presence_never_claims_live(tmp_path: Path) -> None:
    (tmp_path / "module.py").write_text("pass", encoding="utf-8")
    inventory = {
        "policy": {"simulation_counts_as_real": False},
        "components": [{
            "id": "sample",
            "name": "Sample",
            "status": "IMPLEMENTED_UNVERIFIED",
            "code_paths": ["module.py"],
            "real_acceptance": ["health_passed"],
        }],
    }

    report = build_report(inventory, root=tmp_path)

    assert report["live_status_claimed"] is False
    assert report["components"][0]["code_paths_present"] == ["module.py"]
    assert report["components"][0]["source_presence_is_runtime_proof"] is False
    assert report["components"][0]["status"] == "IMPLEMENTED_UNVERIFIED"


def test_missing_source_path_is_reported(tmp_path: Path) -> None:
    report = build_report({
        "components": [{
            "id": "missing",
            "name": "Missing",
            "status": "SIMULATOR_ONLY",
            "code_paths": ["not-here.py"],
        }],
    }, root=tmp_path)

    assert report["components"][0]["code_paths_missing"] == ["not-here.py"]


def test_inventory_has_explicit_real_acceptance_gates() -> None:
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((root / "config" / "real_runtime_migration.json").read_text(encoding="utf-8"))
    assert inventory["policy"]["simulation_counts_as_real"] is False
    assert inventory["policy"]["main_branch_direct_writes_allowed"] is False
    assert all(item.get("real_acceptance") for item in inventory["components"])


def test_cli_json_does_not_claim_live() -> None:
    script = Path(__file__).resolve().parents[1] / "tools" / "brain_real_runtime_migration_audit.py"
    result = subprocess.run(
        [sys.executable, str(script), "--json"],
        check=True, capture_output=True, text=True,
    )
    report = json.loads(result.stdout)
    assert report["mode"] == "read_only_source_audit"
    assert report["live_status_claimed"] is False
    assert report["component_count"] >= 5
