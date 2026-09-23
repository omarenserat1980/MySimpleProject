"""Platform adapter layer for authorized external-work integrations.

Adapters normalize opportunities/actions without storing credentials. Real
platform APIs must be connected through official OAuth/API mechanisms outside
this module.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Protocol


@dataclass(frozen=True)
class ConnectorCapabilities:
    read_opportunities: bool = True
    draft_proposals: bool = True
    submit_proposals: bool = False
    read_orders: bool = False
    read_payouts: bool = False


class PlatformAdapter(Protocol):
    platform: str
    capabilities: ConnectorCapabilities

    def normalize_opportunity(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class BaseAdapter:
    platform = "UNKNOWN"
    capabilities = ConnectorCapabilities()

    def normalize_opportunity(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "title": str(payload.get("title") or payload.get("name") or "Untitled"),
            "description": str(payload.get("description") or ""),
            "skills": tuple(payload.get("skills") or payload.get("tags") or ()),
            "budget_jod": payload.get("budget_jod"),
            "source_url": payload.get("source_url") or payload.get("url"),
        }


class UpworkAdapter(BaseAdapter):
    platform = "UPWORK"


class FiverrAdapter(BaseAdapter):
    platform = "FIVERR"


class FreelancerAdapter(BaseAdapter):
    platform = "FREELANCER"


class MostaqlAdapter(BaseAdapter):
    platform = "MOSTAQL"


class KhamsatAdapter(BaseAdapter):
    platform = "KHAMSAT"


class LinkedInAdapter(BaseAdapter):
    platform = "LINKEDIN"


ADAPTERS = {
    cls().platform: cls for cls in (
        UpworkAdapter, FiverrAdapter, FreelancerAdapter,
        MostaqlAdapter, KhamsatAdapter, LinkedInAdapter,
    )
}


class PlatformAdapterRegistry:
    def __init__(self) -> None:
        self.adapters = {name: cls() for name, cls in ADAPTERS.items()}

    def get(self, platform: str) -> BaseAdapter:
        key = platform.upper()
        if key not in self.adapters:
            raise KeyError(f"No adapter for {platform}")
        return self.adapters[key]

    def capabilities(self) -> dict[str, dict[str, Any]]:
        return {
            name: asdict(adapter.capabilities)
            for name, adapter in self.adapters.items()
        }

    def normalize(self, platform: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.get(platform).normalize_opportunity(payload)
