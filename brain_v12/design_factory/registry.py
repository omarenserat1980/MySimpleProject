"""Prompt inventory and capability metadata for Universal Design Factory."""
from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
PROMPT_DIR = ROOT / "prompts" / "universal_design_factory"
REGISTRY_PATH = ROOT / "brain_v12" / "design_factory" / "registry.json"

def load_registry() -> dict:
    """Load the checked-in registry; fail clearly if missing or malformed."""
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if data.get("version") != "2.0":
        raise ValueError("Unsupported design factory registry version")
    prompts = data.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("Registry must contain a non-empty prompts list")
    ids = [item.get("id") for item in prompts]
    if len(ids) != len(set(ids)):
        raise ValueError("Prompt IDs must be unique")
    return data

def audit_prompt_files() -> dict:
    """Return missing and present prompt paths; does not infer execution capability."""
    registry = load_registry()
    present, missing = [], []
    for item in registry["prompts"]:
        path = ROOT / item["path"]
        (present if path.is_file() else missing).append(item["path"])
    return {
        "status": "PASS" if not missing else "BLOCKED",
        "present": present,
        "missing": missing,
        "prompt_count": len(registry["prompts"]),
        "meaning": "Prompt-file inventory only; does not prove specialist execution capability.",
    }
