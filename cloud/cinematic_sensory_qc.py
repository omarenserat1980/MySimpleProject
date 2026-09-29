"""Sensory QC bridge for cinematic production.

Uses hearing/vision/fu'ad-inspired evidence separation to catch continuity
issues before a film is considered verified. This is an engineering model,
not a metaphysical claim.
"""
from __future__ import annotations

from cloud.sensory_faud_engine import SensoryFuadEngine


class CinematicSensoryQC:
    def __init__(self) -> None:
        self.engine = SensoryFuadEngine()

    def inspect_shot(self, shot_id: str, *, visual: str, audio: str,
                     visual_confidence: float = 1.0,
                     audio_confidence: float = 1.0) -> dict:
        vision = self.engine.observe(
            "vision", {"shot_id": shot_id, "visual": visual},
            visual_confidence, source="cinematic_visual"
        )
        hearing = self.engine.observe(
            "hearing", {"shot_id": shot_id, "audio": audio},
            audio_confidence, source="cinematic_audio"
        )
        return {"shot_id": shot_id, "vision": vision, "hearing": hearing}

    def continuity_check(self, previous: dict, current: dict) -> dict:
        issues = []
        if previous.get("character") != current.get("character"):
            issues.append("character_continuity")
        if previous.get("location") != current.get("location"):
            issues.append("location_continuity")
        if previous.get("time") != current.get("time"):
            issues.append("temporal_continuity")
        if previous.get("audio_signature") != current.get("audio_signature"):
            issues.append("audio_continuity")
        return {
            "ok": not issues,
            "issues": issues,
            "requires_review": bool(issues),
        }

    def integrate_story(self, *, interpretation: str,
                        evidence_ids: list[int] | None = None) -> dict:
        return self.engine.integrate(
            interpretation=interpretation,
            confidence=1.0,
            evidence_ids=evidence_ids,
        )

    def audit(self) -> dict:
        return self.engine.audit()
