"""Top-level capability router for the unified brain."""
from __future__ import annotations

from .multimedia_capability_hub import MultimediaHub
from .software_factory import SUPPORTED_KINDS as SOFTWARE_KINDS
from .web_app_factory import snapshot as web_snapshot
from .app_factory import snapshot as app_snapshot
from .media_production_pipeline import snapshot as media_pipeline_snapshot
from .capability_orchestrator import execution_plan
from .cinematic_director import snapshot as cinematic_director_snapshot
from .cinematic_money_factory import snapshot as cinematic_money_snapshot
from .youtube_publisher import snapshot as youtube_snapshot


class CapabilityHub:
    CAPABILITIES = {
        "software": "software_factory",
        "web": "web_app_factory",
        "app": "app_factory",
        "image": "multimedia_capability_hub",
        "audio": "multimedia_capability_hub",
        "video": "multimedia_capability_hub",
        "design": "multimedia_capability_hub",
        "media_pipeline": "media_production_pipeline",
        "cinematic": "cinematic_director",
        "cinematic_money": "cinematic_money_factory",
        "youtube": "youtube_publisher",
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
        if capability == "app":
            return {"status": "READY", "module": "app_factory",
                    "details": app_snapshot()}
        if capability == "media_pipeline":
            return {"status": "READY", "module": "media_production_pipeline",
                    "details": media_pipeline_snapshot()}
        if capability == "cinematic":
            return {"status": "READY", "module": "cinematic_director",
                    "details": cinematic_director_snapshot()}
        if capability == "cinematic_money":
            return {"status": "READY", "module": "cinematic_money_factory",
                    "details": cinematic_money_snapshot()}
        if capability == "youtube":
            return {"status": "READY", "module": "youtube_publisher",
                    "details": youtube_snapshot()}
        return {"status": "READY", "module": "multimedia_capability_hub",
                "providers": self.media.available_providers(capability)}

    def plan(self, objective: str) -> dict:
        return execution_plan(objective)

    def snapshot(self) -> dict:
        return {
            "capabilities": self.CAPABILITIES,
            "software": sorted(SOFTWARE_KINDS),
            "media": self.media.snapshot(),
            "media_pipeline": media_pipeline_snapshot(),
            "cinematic": cinematic_director_snapshot(),
            "cinematic_money": cinematic_money_snapshot(),
            "youtube": youtube_snapshot(),
            "web": web_snapshot(),
            "app": app_snapshot(),
            "automatic_orchestration": True,
        }
