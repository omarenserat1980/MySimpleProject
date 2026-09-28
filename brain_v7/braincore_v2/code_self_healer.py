"""Bounded source-code self-healer for the Electronic Brain factory.

The healer is deliberately conservative:
- only files in SOURCE_ALLOWLIST may be changed;
- only deterministic repair rules are applied;
- every change is backed up in memory and reverted if verification fails;
- pytest/compile verification is required before a cycle can be accepted;
- at most 100 cycles are attempted.

This tool repairs the checked-out workspace. It does not silently push or
rewrite the Git repository history.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

MAX_CYCLES = 100
ROOT = Path(__file__).resolve().parents[2]
SOURCE_ALLOWLIST = {
    ROOT / "brain_v7/braincore_v2/factory_repair_app.py",
    ROOT / "brain_v7/braincore_v2/brain_media_adapter.py",
    ROOT / ".github/workflows/electronic-brain-cinematic.yml",
}

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")

def _replace_once(path: Path, old: str, new: str) -> bool:
    if path not in SOURCE_ALLOWLIST:
        return False
    text = _read(path)
    if old not in text or new in text:
        return False
    _write(path, text.replace(old, new, 1))
    return True

def rule_empty_fal_model() -> list[str]:
    p = ROOT / "brain_v7/braincore_v2/brain_media_adapter.py"
    old = 'model=os.getenv("FAL_MODEL","fal-ai/kling-video/v3/pro/text-to-video")'
    new = 'model=os.getenv("FAL_MODEL","").strip() or "fal-ai/kling-video/v3/pro/text-to-video"'
    return [str(p.relative_to(ROOT))] if _replace_once(p, old, new) else []

def rule_import_repair_100_test() -> list[str]:
    p = ROOT / "brain_v7/braincore_v2/test_factory_repair_app.py"
    if p.exists() and p not in SOURCE_ALLOWLIST:
        return []
    return []

def rule_workflow_persists_route() -> list[str]:
    p = ROOT / ".github/workflows/electronic-brain-cinematic.yml"
    text = _read(p) if p.exists() else ""
    marker = "Persisted FACTORY_MEDIA_ROUTE="
    if marker in text:
        return []
    needle = 'FACTORY_REPAIR_100=1 python -m brain_v7.braincore_v2.factory_repair_app'
    if needle not in text:
        return []
    block = '''FACTORY_REPAIR_100=1 python -m brain_v7.braincore_v2.factory_repair_app
          test -s factory_repair_100_report.json
          python - <<'PY'
          import json, os
          report=json.load(open("factory_repair_100_report.json", encoding="utf-8"))
          history=report.get("history") or []
          route=(history[-1].get("diagnosis") or {}).get("recommended_route") if history else None
          if route and route != "configuration_required":
              with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as fh:
                  fh.write(f"FACTORY_MEDIA_ROUTE={route}\\n")
              print(f"Persisted FACTORY_MEDIA_ROUTE={route}")
          PY'''
    return [str(p.relative_to(ROOT))] if _replace_once(p, needle, block) else []

RULES: tuple[Callable[[], list[str]], ...] = (
    rule_empty_fal_model,
    rule_workflow_persists_route,
)

def verify() -> tuple[bool, str]:
    compile_cmd = ["python", "-m", "compileall", "-q", "brain_v7/braincore_v2"]
    p = subprocess.run(compile_cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    if p.returncode:
        return False, (p.stdout + p.stderr)[-4000:]
    test = subprocess.run(
        ["python", "-m", "pytest", "-q", "brain_v7/braincore_v2/test_factory_repair_app.py"],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
    )
    return test.returncode == 0, (test.stdout + test.stderr)[-4000:]

def _snapshot(paths: list[Path]) -> dict[Path, str]:
    return {path: _read(path) for path in paths if path.exists()}

def _restore(snapshot: dict[Path, str]) -> None:
    for path, content in snapshot.items():
        _write(path, content)

def heal(error_text: str = "", report_path: str = "code_self_healer_report.json") -> dict:
    history = []
    last_error = error_text
    for cycle in range(1, MAX_CYCLES + 1):
        before = _snapshot(list(SOURCE_ALLOWLIST))
        changed = []
        rule_errors = []
        for rule in RULES:
            try:
                changed.extend(rule())
            except Exception as exc:
                rule_errors.append(str(exc))
                last_error = str(exc)
        ok, verification = verify()
        rolled_back = bool(changed) and not ok
        if rolled_back:
            _restore(before)
        entry = {
            "cycle": cycle,
            "changed_files": sorted(set(changed)),
            "rule_errors": rule_errors,
            "verification_passed": ok,
            "verification_tail": verification,
            "rolled_back": rolled_back,
        }
        history.append(entry)
        if ok:
            result = {
                "status": "CODE_VERIFIED",
                "cycles_completed": cycle,
                "changed_files": sorted(set(changed)),
                "history": history,
                "last_error": last_error,
                "note": "Source was verified in the current workspace; repository persistence requires a reviewed commit.",
            }
            Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return result
        last_error = verification
    result = {
        "status": "CODE_REPAIR_LIMIT_REACHED",
        "cycles_completed": MAX_CYCLES,
        "history": history,
        "last_error": last_error,
    }
    Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

if __name__ == "__main__":
    result = heal(os.getenv("FACTORY_LAST_ERROR", ""))
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "CODE_VERIFIED" else 2)
