"""Read-only API exposing the fail-closed mining evidence gate."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from .asic_readonly_connector import collect_asic_status
from .mining_readiness_gate import evaluate_mining_readiness

router = APIRouter(prefix="/api/mining", tags=["mining-readiness"])
_EVIDENCE_PATH = Path(__file__).resolve().parents[2] / "evidence" / "ckpool-readonly-verification.json"


def _load_ckpool_evidence() -> dict[str, Any]:
    try:
        value = json.loads(_EVIDENCE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


@router.get("/readiness")
def mining_readiness_status() -> dict[str, Any]:
    """Classify current local evidence without starting miners or scanning the LAN."""
    asic = collect_asic_status()
    # Only a configured public payout address is checked; its value is never returned.
    payout_configured = bool(os.getenv("BRAIN_BTC_PAYOUT_ADDRESS", "").strip())
    return evaluate_mining_readiness(
        asic_status=asic,
        ckpool_evidence=_load_ckpool_evidence(),
        payout_address_configured=payout_configured,
    )
