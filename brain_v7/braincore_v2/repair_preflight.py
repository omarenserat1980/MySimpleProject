"""Deterministic preflight gate for Electronic Brain repair/production workflows.

This gate runs before expensive repair/factory work. It checks dependencies,
workflow syntax, repair imports, required tests, FFmpeg/ffprobe and whether at
least one authorized media route is available. It never prints secret values.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = [
    ROOT / ".github/workflows/brain-auto-repair-and-smoke.yml",
    ROOT / ".github/workflows/brain-15000-auto-repair.yml",
    ROOT / ".github/workflows/brain6-168h-cloud.yml",
]
MODULES = [
    "brain_v7.braincore_v2.repair_controller_15000",
    "brain_v7.braincore_v2.code_self_healer",
    "brain_v7.braincore_v2.brain_media_adapter",
    "brain_v7.braincore_v2.cinematic_local_renderer",
]
TESTS = [
    ROOT / "brain_v7/braincore_v2/test_factory_repair_app.py",
    ROOT / "brain_v7/braincore_v2/test_code_repair_app.py",
    ROOT / "brain_v7/braincore_v2/test_cinematic_local_renderer.py",
]


def _truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def check_command(name: str, version_arg: str = "-version") -> dict[str, Any]:
    path = shutil.which(name)
    if not path:
        return {"name": name, "available": False}
    try:
        p = subprocess.run([path, version_arg], capture_output=True, text=True, timeout=15)
        return {"name": name, "available": p.returncode == 0}
    except Exception as exc:
        return {"name": name, "available": False, "error": f"{type(exc).__name__}: {exc}"}


def check_module(name: str) -> dict[str, Any]:
    try:
        importlib.import_module(name)
        return {"name": name, "available": True}
    except Exception as exc:
        return {"name": name, "available": False, "error": f"{type(exc).__name__}: {exc}"}


def check_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path.relative_to(ROOT)), "valid": False, "error": "missing"}
    try:
        import yaml  # type: ignore
        yaml.safe_load(path.read_text(encoding="utf-8"))
        return {"path": str(path.relative_to(ROOT)), "valid": True}
    except ImportError:
        try:
            p = subprocess.run(
                ["ruby", "-e", "require 'yaml'; YAML.load_file(ARGV[0])", str(path)],
                capture_output=True, text=True, timeout=15,
            )
            return {"path": str(path.relative_to(ROOT)), "valid": p.returncode == 0,
                    "error": p.stderr[-500:] if p.returncode else None}
        except Exception as exc:
            return {"path": str(path.relative_to(ROOT)), "valid": False, "error": repr(exc)}
    except Exception as exc:
        return {"path": str(path.relative_to(ROOT)), "valid": False,
                "error": f"{type(exc).__name__}: {exc}"}


def run_preflight(report_path: str = "repair_preflight_report.json") -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "PREFLIGHT_OK",
        "python": check_command("python", "--version"),
        "ffmpeg": check_command(os.getenv("FFMPEG_BIN", "ffmpeg")),
        "ffprobe": check_command(os.getenv("FFPROBE_BIN", "ffprobe")),
        "modules": [check_module(x) for x in MODULES],
        "workflows": [check_yaml(x) for x in WORKFLOWS],
        "tests": [{"path": str(x.relative_to(ROOT)), "exists": x.exists()} for x in TESTS],
        "media_route": {
            "local_ffmpeg": _truthy("FACTORY_ALLOW_LOCAL_FALLBACK", "0"),
            "fal": bool(os.getenv("FAL_KEY", "").strip()),
            "media_provider": bool(os.getenv("MEDIA_PROVIDER_URL", "").strip()),
            "comfyui": bool(os.getenv("COMFYUI_URL", "").strip()),
        },
        "secret_presence_only": {
            "FAL_KEY": bool(os.getenv("FAL_KEY", "").strip()),
            "MEDIA_PROVIDER_API_KEY": bool(os.getenv("MEDIA_PROVIDER_API_KEY", "").strip()),
            "COMFYUI_WORKFLOW_JSON": bool(os.getenv("COMFYUI_WORKFLOW_JSON", "").strip()),
        },
    }
    failures: list[str] = []
    failures += ["python"] if not result["python"]["available"] else []
    failures += ["ffmpeg"] if not result["ffmpeg"]["available"] else []
    failures += ["ffprobe"] if not result["ffprobe"]["available"] else []
    failures += [x["name"] for x in result["modules"] if not x["available"]]
    failures += [x["path"] for x in result["workflows"] if not x["valid"]]
    failures += [x["path"] for x in result["tests"] if not x["exists"]]
    if not any(result["media_route"].values()):
        failures.append("no_media_route_enabled")
    result["failures"] = failures
    if failures:
        result["status"] = "PREFLIGHT_FAILED"
    Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="repair_preflight_report.json")
    args = parser.parse_args()
    result = run_preflight(args.report)
    print(json.dumps({"status": result["status"], "failures": result["failures"]}, ensure_ascii=False))
    return 0 if result["status"] == "PREFLIGHT_OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
