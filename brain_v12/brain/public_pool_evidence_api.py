"""Authenticated, opt-in persistence of preconfigured local Public Pool evidence.

This endpoint only reads files under the configured evidence root and appends an
UNVERIFIED diagnostic record. It never contacts a pool or starts/stops a miner.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .control_auth import require_control_key
from .public_pool_evidence_runtime_adapter import persist_public_pool_evidence


def create_public_pool_evidence_router(evidence_store: Any) -> APIRouter:
    router = APIRouter(prefix="/api/mining-node/pool-evidence", tags=["Public Pool Evidence"])

    @router.post("/record")
    def record_configured_evidence(request: Request) -> dict[str, Any]:
        """Persist one classification using only server-configured, bounded paths."""
        require_control_key(request)
        root_value = os.getenv("BRAIN_PUBLIC_POOL_EVIDENCE_ROOT", "~/.brain/evidence")
        root = Path(root_value).expanduser().resolve()

        def trusted_configured_path(env_name: str, default_name: str) -> Path | None:
            configured = os.getenv(env_name, str(root / default_name)).strip()
            if not configured:
                return None
            candidate = Path(configured).expanduser().resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="EVIDENCE_PATH_OUTSIDE_CONFIGURED_ROOT") from exc
            if not candidate.is_file():
                return None
            return candidate

        try:
            miner_log = trusted_configured_path("BRAIN_PUBLIC_POOL_MINER_LOG", "public-pool-debug.log")
            snapshot = trusted_configured_path("BRAIN_PUBLIC_POOL_SNAPSHOT", "public-pool-latest.json")
            result = persist_public_pool_evidence(
                evidence_store,
                "public-pool-protected-diagnostic",
                miner_log_path=miner_log,
                pool_snapshot_path=snapshot,
                phase="read_only_diagnostic",
            )
        except HTTPException:
            raise
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="PUBLIC_POOL_EVIDENCE_READ_FAILED") from exc

        result["status"] = "UNVERIFIED_DIAGNOSTIC_PERSISTED"
        result["network_access_performed"] = False
        result["miner_started_or_stopped"] = False
        result["pool_settings_changed"] = False
        result["accepted_shares_verified"] = False
        result["revenue_verified"] = False
        result["payout_verified"] = False
        return result

    return router
