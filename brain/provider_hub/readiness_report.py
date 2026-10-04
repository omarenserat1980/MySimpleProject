"""Machine-readable commercial readiness report for BRAIN."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from brain.provider_hub.commercial_gate import CommercialReadiness


def build_report(readiness: CommercialReadiness, output: str | Path) -> dict:
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": readiness.status,
        "checks": {
            "public_api": readiness.public_api,
            "auth_verified": readiness.auth_verified,
            "trial_enforced": readiness.trial_enforced,
            "order_flow_verified": readiness.order_flow_verified,
            "payment_provider_active": readiness.payment_provider_active,
            "payment_verification_live": readiness.payment_verification_live,
            "delivery_verified": readiness.delivery_verified,
            "evidence_generated": readiness.evidence_generated,
        },
        "blockers": list(readiness.blockers),
    }
    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
