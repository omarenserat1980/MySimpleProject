"""Top-level capability router for the unified brain."""
from __future__ import annotations

from .multimedia_capability_hub import MultimediaHub
from .software_factory import SUPPORTED_KINDS as SOFTWARE_KINDS
from .web_app_factory import snapshot as web_snapshot
from .capability_orchestrator import build_plan, execution_plan


class CapabilityHub:
    CAPABILITIES = {
        "software": "software_factory",
        "web": "web_app_factory",
        "image": "multimedia_capability_hub",
        "audio": "multimedia_capability_hub",
        "video": "multimedia_capability_hub",
        "design": "multimedia_capability_hub",
    }

    def __init__(self):
        self.media = MultimediaHub()

    def route(self, capability: str) -> dict:
        capability = capability.lower().strip()
        if capability not in self.CAPABILITIES:
            return {"status": "UNSUPPORTED_CAPABILITY", "capability": capability}
        if capability == "software":
            return {"status": "READY", "module": "software_factory",
                    "kinds": sorted(SOFTWARE_KINDS)}
        if capability == "web":
            return {"status": "READY", "module": "web_app_factory",
                    "details": web_snapshot()}
        return {"status": "READY", "module": "multimedia_capability_hub",
                "providers": self.media.available_providers(capability)}

    def plan(self, objective: str) -> dict:
        return execution_plan(objective)

    def snapshot(self) -> dict:
        return {
            "capabilities": self.CAPABILITIES,
            "software": sorted(SOFTWARE_KINDS),
            "media": self.media.snapshot(),
            "web": web_snapshot(),
            "automatic_orchestration": True,
        }
