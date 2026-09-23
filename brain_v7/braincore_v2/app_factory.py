"""Dedicated planning layer for mobile and application products.

Provider-neutral: it plans Android/mobile/desktop applications and does not
publish or access credentials by itself.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


SUPPORTED_PLATFORMS = ("android", "ios", "web_mobile", "desktop")


@dataclass(frozen=True)
class AppSpec:
    name: str
    platform: str
    objective: str
    rtl: bool = True
    responsive: bool = True
    api: bool = True
    database: bool = True


def plan_app(
    objective: str,
    *,
    name: str = "Generated App",
    platform: str = "android",
    rtl: bool = True,
    api: bool = True,
    database: bool = True,
) -> AppSpec:
    platform = platform.lower().strip()
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")
    return AppSpec(
        name=name,
        platform=platform,
        objective=objective,
        rtl=rtl,
        responsive=True,
        api=api,
        database=database,
    )


def implementation_stages(spec: AppSpec) -> list[str]:
    return [
        "SPECIFY",
        "UX_FLOW",
        "UI_SCAFFOLD",
        "IMPLEMENT",
        "API_INTEGRATION" if spec.api else "LOCAL_DATA",
        "DATABASE" if spec.database else "NO_DATABASE",
        "VERIFY_LOCAL",
        "PACKAGE",
        "LEARN_AND_REPLAN",
    ]


def snapshot() -> dict[str, Any]:
    return {
        "supported_platforms": list(SUPPORTED_PLATFORMS),
        "local_generation": True,
        "external_publish": "permission_gated",
        "credential_access": False,
    }
