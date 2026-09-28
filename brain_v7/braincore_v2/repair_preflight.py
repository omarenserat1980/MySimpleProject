"""Deterministic preflight for Electronic Brain repair/production workflows.

Checks the local checkout before expensive repair/factory work:
- required Python modules
- FFmpeg availability
- workflow YAML parsing
- Brain repair modules importing cleanly
- required test files existing

No network calls, no secrets, and no source mutation.
"""
from __future__ import annotations

import importlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = [
    ROOT / ".github/workflows/brain-15000-auto-repair.yml",
]
MODULES = [
    "brain_v7.braincore_v2.repair_controller_15000",
    "brain_v7.braincore_v2.code_self_healer",
]
TESTS = [
    ROOT / "brain_v7/braincore_v2/test_factory_repair_app.py",
    ROOT / "brain_v7/braincore_v2/test_code_repair_app.py",
    ROOT / "brain_v7/braincore_v2/test_cinematic_local_renderer.py",
]


def check_command(name: str) -> dict:
    return {"name": name, "available": shutil.which(name) is not None}


def check_module(name: str) -> dict:
    try:
        importlib.import_module(name)
        return {"name": name, "available": True}
    except Exception as exc:
        return {"name": name, "available": False, "error": f"{type(exc).__name__}: {exc}"}


def check_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
        yaml.safe_load(path.read_text(encoding="utf-8"))
        return {"path": str(path.relative_to(ROOT)), "valid": True}
    except Exception as exc:
        return {"path": str(path.relative_to(ROOT)), "valid": False, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    result = {
        "status": "PREFLIGHT_OK",
        "python": check_command("python"),
        "ffmpeg": check_command("ffmpeg"),
        "modules": [check_module(x) for x in MODULES],
        "workflows": [check_yaml(x) for x in WORKFLOWS],
        "tests": [{"path": str(x.relative_to(ROOT)), "exists": x.exists()} for x in TESTS],
    }
    failures = []
    if not result["python"]["available"]:
        failures.append("python")
    if not result["ffmpeg"]["available"]:
        failures.append("ffmpeg")
    failures += [x["name"] for x in result["modules"] if not x["available"]]
    failures += [x["path"] for x in result["workflows"] if not x["valid"]]
    failures += [x["path"] for x in result["tests"] if not x["exists"]]
    if failures:
        result["status"] = "PREFLIGHT_FAILED"
        result["failures"] = failures
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PREFLIGHT_OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
