"""Canonical APM BUILD stage profiles for existing Brain pipelines."""

from __future__ import annotations

from .apm_stage_discovery import StageDiscovery, from_mapping, from_module


def cognitive_v12_profile() -> StageDiscovery:
    """Discover the V12 cognitive loop conservatively as a dependency chain."""
    return from_module(
        "brain_v12.brain.cognitive_loop",
        attribute="STAGES",
        policy="sequential",
    )


def readiness_profile() -> StageDiscovery:
    """Explicit readiness graph; only independently evaluable gates fan out."""
    declarations = [
        {"id": "S1", "metadata": {"label": "COGNITION_MEMORY"}},
        {"id": "S2", "depends_on": ["S1"], "metadata": {"label": "ORGANIZATION_WORKFORCE"}},
        {"id": "S3", "depends_on": ["S2"], "metadata": {"label": "REVENUE_EXPERIMENTS"}},
        {"id": "S4", "depends_on": ["S2"], "metadata": {"label": "EXTERNAL_WORK_COMPLIANCE"}},
        {"id": "S5", "depends_on": ["S1"], "metadata": {"label": "CINEMATIC_PRODUCTION"}},
        {"id": "S8", "depends_on": ["S1"], "metadata": {"label": "SECURITY_SAFETY"}},
        {"id": "S10", "depends_on": ["S1"], "metadata": {"label": "CODE_TOOL_SELF_DEVELOPMENT"}},
        {"id": "S6", "depends_on": ["S4", "S5"], "metadata": {"label": "YOUTUBE_PUBLICATION"}},
        {"id": "S7", "depends_on": ["S6"], "metadata": {"label": "ANALYTICS_LEARNING"}},
        {"id": "S9", "depends_on": ["S4", "S8"], "metadata": {"label": "DEPLOYMENT_READINESS"}},
        {"id": "S11", "depends_on": ["S10"], "metadata": {"label": "CONTINUOUS_SELF_IMPROVEMENT"}},
    ]
    return from_mapping(declarations, source="completion_orchestrator.STAGES.apm")


def discover_profile(name: str) -> StageDiscovery:
    profiles = {
        "cognitive_v12": cognitive_v12_profile,
        "readiness": readiness_profile,
    }
    try:
        return profiles[name]()
    except KeyError as exc:
        raise ValueError(f"unknown APM profile: {name}") from exc
