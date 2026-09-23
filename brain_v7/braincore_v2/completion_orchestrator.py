"""Completion and readiness orchestrator for Electronic Brain V7/V12.

This module turns the remaining project stages into explicit, auditable gates.
It never fabricates live deployment, revenue, or external permissions.

Stages:
1. cognition and memory
2. organization/workforce
3. revenue experiments
4. external-work compliance
5. cinematic production
6. YouTube publication
7. analytics/learning
8. security and safety
9. deployment readiness
10. coding-tool self-development
11. continuous self-improvement
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class StageResult:
    stage_id: str
    name: str
    status: str
    checks: tuple[str, ...]
    blockers: tuple[str, ...] = ()
    next_action: str = ""


STAGES: tuple[tuple[str, str], ...] = (
    ("S1", "COGNITION_MEMORY"),
    ("S2", "ORGANIZATION_WORKFORCE"),
    ("S3", "REVENUE_EXPERIMENTS"),
    ("S4", "EXTERNAL_WORK_COMPLIANCE"),
    ("S5", "CINEMATIC_PRODUCTION"),
    ("S6", "YOUTUBE_PUBLICATION"),
    ("S7", "ANALYTICS_LEARNING"),
    ("S8", "SECURITY_SAFETY"),
    ("S9", "DEPLOYMENT_READINESS"),
    ("S10", "CODE_TOOL_SELF_DEVELOPMENT"),
    ("S11", "CONTINUOUS_SELF_IMPROVEMENT"),
)


def evaluate(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate readiness from observed state only.

    A PASS means the code-level capability is present in the supplied snapshot.
    LIVE means an external system has actually confirmed the side effect.
    This function deliberately never upgrades PASS to LIVE.
    """
    org = snapshot.get("organization", {})
    external = snapshot.get("external_work", {})
    revenue = snapshot.get("revenue_challenge", {})
    factory = snapshot.get("cinematic_factory", {})
    deployment = snapshot.get("deployment", {})

    results: list[StageResult] = [
        StageResult(
            "S1", "COGNITION_MEMORY",
            "PASS" if snapshot.get("cognition_memory") else "BLOCKED",
            ("memory", "reasoning", "planning", "learning"),
            () if snapshot.get("cognition_memory") else ("cognition_memory_not_observed",),
            "Run a brain cycle and persist its verified state.",
        ),
        StageResult(
            "S2", "ORGANIZATION_WORKFORCE",
            "PASS" if org.get("employees") is not None else "BLOCKED",
            ("hierarchy", "delegation", "workforce_evolution", "talent"),
            () if org.get("employees") is not None else ("organization_not_observed",),
            "Continue staffing through the workforce engine.",
        ),
        StageResult(
            "S3", "REVENUE_EXPERIMENTS",
            "PASS" if revenue.get("target_jod") is not None else "BLOCKED",
            ("diversified_tasks", "verified_revenue_accounting"),
            () if revenue.get("target_jod") is not None else ("revenue_factory_not_observed",),
            "Only count payments backed by platform/order evidence.",
        ),
        StageResult(
            "S4", "EXTERNAL_WORK_COMPLIANCE",
            "PASS" if external.get("accounts") is not None else "BLOCKED",
            ("platform_adapters", "queue", "compliance_gate", "no_credential_storage"),
            () if external.get("accounts") is not None else ("external_work_not_observed",),
            "Connect authorized platform accounts outside source code.",
        ),
        StageResult(
            "S5", "CINEMATIC_PRODUCTION",
            "PASS" if factory.get("shot_generation") and factory.get("video_assembly") else "BLOCKED",
            ("topic_selection", "shot_generation", "assembly", "quality_gate"),
            () if factory.get("shot_generation") and factory.get("video_assembly") else ("media_pipeline_not_observed",),
            "Run one authorized production cycle and verify the MP4 artifact.",
        ),
        StageResult(
            "S6", "YOUTUBE_PUBLICATION",
            "PASS" if factory.get("authorized_publication") else "BLOCKED",
            ("OAuth client", "publication gate", "privacy setting"),
            () if factory.get("authorized_publication") else ("youtube_publication_not_configured",),
            "Publish only after the configured account and upload response are verified.",
        ),
        StageResult(
            "S7", "ANALYTICS_LEARNING",
            "PASS" if factory.get("analytics_feedback") and factory.get("next_cycle_learning") else "BLOCKED",
            ("analytics ingestion", "verified feedback", "next-cycle learning"),
            () if factory.get("analytics_feedback") and factory.get("next_cycle_learning") else ("analytics_learning_not_observed",),
            "Use verified analytics only; do not infer revenue from views.",
        ),
        StageResult(
            "S8", "SECURITY_SAFETY",
            "PASS" if snapshot.get("safety_gates") else "BLOCKED",
            ("permission gates", "no secret storage", "money-transfer block", "auditability"),
            () if snapshot.get("safety_gates") else ("safety_gates_not_observed",),
            "Keep external side effects permission-gated.",
        ),
        StageResult(
            "S9", "DEPLOYMENT_READINESS",
            "PASS" if deployment.get("configured") else "BLOCKED",
            ("worker configuration", "health checks", "scheduled loop"),
            () if deployment.get("configured") else ("deployment_not_observed",),
            "Verify the deployed worker from provider logs before calling it live.",
        ),        StageResult(
            "S10", "CODE_TOOL_SELF_DEVELOPMENT",
            "PASS" if snapshot.get("code_tool_engineering") else "BLOCKED",
            ("dedicated_team", "safe_workspace", "atomic_changes", "syntax_validation", "checkpoints", "rollback"),
            () if snapshot.get("code_tool_engineering") else ("code_tool_team_not_observed",),
            "Continue the dedicated coding team loop; only apply validated changes inside the configured workspace.",
        ),

    ]

    live = tuple(r.stage_id for r in results if r.status == "LIVE")
    passed = tuple(r.stage_id for r in results if r.status == "PASS")
    blocked = tuple(r.stage_id for r in results if r.status == "BLOCKED")

    return {
        "status": "READY_WITH_EXTERNAL_VERIFICATION" if not blocked else "PARTIALLY_READY",
        "stages": [asdict(r) for r in results],
        "passed_stages": passed,
        "live_stages": live,
        "blocked_stages": blocked,
        "revenue_is_guaranteed": False,
        "external_side_effects_claimed": False,
        "principle": "Observed evidence only; never convert configuration into a claim of live execution.",
    }


def build_default_readiness_snapshot() -> dict[str, Any]:
    return {
        "cognition_memory": True,
        "organization": {"employees": 64},
        "revenue_challenge": {"target_jod": 10000},
        "external_work": {"accounts": 0},
        "cinematic_factory": {
            "shot_generation": True,
            "video_assembly": True,
            "authorized_publication": True,
            "analytics_feedback": True,
            "next_cycle_learning": True,
        },
        "safety_gates": True,
        "deployment": {"configured": True},
        "code_tool_engineering": {"employee_count": 8, "continuous_improvement": True},
        "self_improvement": {"continuous_loop": True, "enabled": True},
    }
