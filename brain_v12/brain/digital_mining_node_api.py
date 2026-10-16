"""Protected read-only API for local Brain mining-node preflight."""
from __future__ import annotations

from fastapi import APIRouter, Request

from .control_auth import require_control_key
from .digital_mining_node import inspect_node

router = APIRouter(prefix="/api/mining-node", tags=["Brain Mining Node"])


@router.get("/local-preflight")
def local_preflight(request: Request) -> dict:
    """Inspect this Brain host; this is not remote attestation or mining proof."""
    require_control_key(request)
    return inspect_node()
