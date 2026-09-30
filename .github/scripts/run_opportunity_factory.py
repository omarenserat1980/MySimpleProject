#!/usr/bin/env python3
"""Brain 6 Opportunity Factory orchestration.

Runs local catalog generation, optional live public discovery, lifecycle refresh,
and writes auditable JSON artifacts. It never submits applications, logs in,
moves money, or claims expected value as realized revenue.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from brain_v7.braincore_v2.revenue_engine import rank_with_financials
from brain_v7.braincore_v2.self_executable_opportunities import catalog as self_catalog
from brain_v7.braincore_v2.api_executable_opportunities import catalog as api_catalog
from brain_v7.braincore_v2.revenue_target_engine import PATHS
from brain_v12.brain.income_engine import IncomeEngine
from brain_v12.brain.live_opportunity_researcher import LiveOpportunityResearcher
from brain_v12.brain.memory import MemoryStore
from brain_v12.brain.economic_ledger import EconomicLedger

ROOT = Path(".")
ARTIFACTS = ROOT / "brain6_artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(name: str, payload: dict) -> None:
    (ARTIFACTS / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    live = os.getenv("LIVE_SEARCH", "true").lower() in {"1", "true", "yes", "on"}
    db_path = os.getenv("BRAIN6_DB", str(ARTIFACTS / "opportunities.db"))

    store = MemoryStore(db_path)
    store.init()
    engine = IncomeEngine(store)

    catalog = {
        "generated_at": now(),
        "financial_opportunities": rank_with_financials(),
        "self_executable": self_catalog(),
        "api_routes": api_catalog(),
        "revenue_paths": [x.__dict__ for x in PATHS],
        "execution_policy": {
            "external_submission": False,
            "money_movement": False,
            "payment_claims_without_evidence": False,
        },
    }
    write_json("opportunity_catalog.json", catalog)

    discovery = {
        "enabled": live,
        "started_at": now(),
        "received": 0,
        "accepted": 0,
        "errors": [],
    }
    if live:
        result = LiveOpportunityResearcher(engine, store).run_once()
        discovery.update(result)
    discovery["finished_at"] = now()
    write_json("live_discovery.json", discovery)

    # Autonomous freelance preparation: discovery -> technical fit -> proposal draft.
    # External submission, login, contracts and money movement remain explicitly gated.
    from brain_v12.brain.freelance_agent import FreelanceAgent
    freelance = FreelanceAgent(store)
    live_rows = engine.prioritize(100)
    prepared = []
    for opportunity in live_rows:
        data = dict(opportunity.get("data") or {})
        if data.get("source_kind") != "LIVE_OPPORTUNITY":
            continue
        candidate = {
            "title": data.get("title") or opportunity.get("title"),
            "url": data.get("source_url") or opportunity.get("source_url"),
            "source_url": data.get("source_url"),
            "requirements": data.get("requirements", ""),
            "description": data.get("requirements", ""),
            "category": data.get("category", "FREELANCE_JOB"),
            "budget": data.get("budget"),
            "evidence": data.get("evidence", ""),
        }
        analysis = freelance.analyze(candidate)
        if analysis.get("recommendation") != "PREPARE_OFFER":
            continue
        offer = freelance.prepare_offer(candidate)
        prepared.append({
            "opportunity_id": data.get("opportunity_id") or opportunity.get("opportunity_id"),
            "title": candidate["title"],
            "url": candidate["url"],
            "fit_score": analysis["fit_score"],
            "categories": analysis["categories"],
            "matched_skills": analysis["matched_skills"],
            "proposal": offer["proposal"],
            "submission_status": "NOT_SUBMITTED",
            "human_gate": "REVIEW_AND_SUBMIT",
        })
        if len(prepared) >= 10:
            break
    prepared.sort(key=lambda x: x["fit_score"], reverse=True)
    write_json("freelance_ready_offers.json", {
        "generated_at": now(),
        "count": len(prepared),
        "offers": prepared,
        "policy": {
            "discovery": "AUTOMATED",
            "technical_fit": "AUTOMATED",
            "proposal_generation": "AUTOMATED",
            "external_submission": "HUMAN_CONTROLLED",
            "client_messages": "HUMAN_CONTROLLED",
            "contracts": "HUMAN_CONTROLLED",
            "payment_movement": "HUMAN_CONTROLLED",
        },
    })

    lifecycle = engine.refresh_lifecycle(
        max_age_hours=float(os.getenv("OPPORTUNITY_MAX_AGE_HOURS", "72")),
        limit=500,
    )
    write_json("lifecycle_refresh.json", lifecycle)

    ledger = EconomicLedger(str(ARTIFACTS / "economy" / "ledger.jsonl"))
    write_json("economic_ledger_snapshot.json", ledger.snapshot())

    report = engine.lifecycle_report(limit=100)
    snapshot = engine.snapshot()
    write_json("opportunity_report.json", {
        "generated_at": now(),
        "discovery": discovery,
        "lifecycle": lifecycle,
        "snapshot": snapshot,
        "policy": "Opportunity evidence is not revenue; revenue requires verified payment evidence.",
    })

    print(json.dumps({
        "ok": True,
        "live_search": live,
        "received": discovery.get("received", 0),
        "accepted": discovery.get("accepted", 0),
        "stale": lifecycle.get("stale", 0),
        "verified_revenue_jod": snapshot.get("verified_revenue_jod", 0),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
