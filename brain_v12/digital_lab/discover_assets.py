"""Read-only inventory generator for Brain Digital Lab.

Scans repository paths and emits metadata only; never reads file contents,
executes discovered files, contacts devices, or modifies source assets.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__",
                 ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build"}
GENERATED_FILES = {"brain-digital-lab-inventory.json"}

def classify(path: Path) -> str:
    parts = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    suffix = path.suffix.lower()
    if len(parts) >= 2 and parts[0] == ".github" and parts[1] == "workflows":
        return "workflow"
    if any(part in {"asic", "rtl", "verilog", "gdsii"} for part in parts[:-1]) or suffix in {".v", ".sv", ".vhd", ".vhdl"}:
        return "asic_rtl"
    if any(part in {"terraform", "infra", "infrastructure", "k8s", "helm"} for part in parts[:-1]) or name in {"dockerfile", "docker-compose.yml", "compose.yml"}:
        return "infrastructure"
    if any(part in {"android", "mobile", "frontend", "web", "app", "apps"} for part in parts[:-1]) or suffix in {".apk", ".aab"}:
        return "application"
    if suffix in {".py", ".sh", ".ps1", ".bat", ".cmd", ".js", ".ts", ".go", ".rs"}:
        return "code_or_script"
    if suffix in {".yml", ".yaml", ".toml", ".ini", ".cfg", ".json"}:
        return "configuration_or_manifest"
    if suffix in {".md", ".rst", ".txt"}:
        return "documentation"
    return "other_file"

def git_commit(root: Path) -> str | None:
    env_sha = os.environ.get("GITHUB_SHA")
    if env_sha:
        return env_sha
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None

def iter_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for filename in sorted(files):
            if filename.lower() in GENERATED_FILES:
                continue
            full = Path(current) / filename
            try:
                if full.is_file() and not full.is_symlink():
                    yield full
            except OSError:
                continue

def build_inventory(root: Path) -> dict:
    root = root.resolve()
    assets = []
    for file_path in iter_files(root):
        try:
            relative = file_path.relative_to(root).as_posix()
            stat = file_path.stat()
        except (OSError, ValueError):
            continue
        assets.append({
            "asset_id": relative,
            "path": relative,
            "domain": classify(Path(relative)),
            "size_bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "lifecycle_status": "DISCOVERED_NOT_TESTED",
            "verification_status": "NOT_RUN",
            "evidence": [],
        })
    return {
        "schema_version": 1,
        "inventory_type": "repository_path_metadata_only",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(root),
        "commit_sha": git_commit(root),
        "asset_count": len(assets),
        "coverage_limitations": [
            "This report covers discoverable repository files only.",
            "It does not prove runtime health, deployment state, device reachability, or physical hardware existence.",
            "File contents are not read and discovered code is not executed.",
            "Unreachable devices, external services, and untracked assets require separate inventory sources.",
        ],
        "assets": assets,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    parser.add_argument("--output", type=Path, default=Path("brain-digital-lab-inventory.json"), help="output JSON path")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"root is not a directory: {root}")
    report = build_inventory(root)
    output = args.output if args.output.is_absolute() else Path.cwd() / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "INVENTORY_GENERATED", "asset_count": report["asset_count"],
                      "output": str(output), "commit_sha": report["commit_sha"]}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())