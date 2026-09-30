"""Machine-readable integration policy and provenance manifest."""
from __future__ import annotations
import json
from pathlib import Path
from .adapter_registry import REGISTRY

PROJECT_POLICIES = {
    "Qwen-Agent": {"license":"Apache-2.0","code_mode":"adapter","models":"verify-model-license"},
    "PaddleOCR": {"license":"Apache-2.0","code_mode":"adapter","models":"verify-model-license"},
    "VoicEra": {"license":"Apache-2.0","code_mode":"adapter","models":"verify-provider/model-license"},
}

def build_manifest() -> dict:
    return {
        "schema":"brain-external-integration/v1",
        "default_activation":"disabled-until-verified",
        "projects": PROJECT_POLICIES,
        "adapters":[x.__dict__ for x in REGISTRY],
    }

def write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_manifest(), ensure_ascii=False, indent=2), encoding="utf-8")
