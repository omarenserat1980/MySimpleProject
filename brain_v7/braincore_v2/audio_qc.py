"""Provider-neutral audio continuity and evidence gate."""
from __future__ import annotations
from typing import Any

def evaluate_audio_evidence(shot: dict[str, Any], result: dict[str, Any], memory: dict[str, Any] | None = None) -> dict[str, Any]:
    memory = memory or {}
    evidence = result.get("audio_qc") or result.get("audio_evidence") or {}
    errors: list[str] = []
    explicit_silence = str(shot.get("audio_mode", "")).lower() in {"silent", "none"}
    if not explicit_silence and not shot.get("voice_prompt") and not shot.get("sound_design_prompt"):
        errors.append("audio_intent_missing")
    if isinstance(evidence, dict):
        status = str(evidence.get("status", "")).upper()
        if status in {"FAIL", "FAILED", "REJECTED"}:
            errors.extend(str(x) for x in (evidence.get("issues") or ["audio_provider_rejected"]))
        score = evidence.get("score")
    else:
        score = None
    if score is None:
        # Absence of provider audio evidence is not a pass. For silent shots,
        # an explicit silent intent is sufficient.
        status = "VERIFIED" if explicit_silence and not errors else ("REPAIR" if errors else "UNVERIFIED")
        return {"status": status, "score": 1.0 if explicit_silence else 0.0,
                "evidence": "explicit_silence" if explicit_silence else "prompt_only",
                "checks": {"speaker_lock": bool(shot.get("voice_prompt")),
                           "acoustic_continuity": bool(memory.get("spaces") or shot.get("sound_design_prompt")),
                           "motif_continuity": bool(memory.get("motifs") or shot.get("sound_design_prompt"))},
                "issues": errors}
    try:
        score = max(0.0, min(1.0, float(score)))
    except Exception:
        score = 0.0
        errors.append("audio_score_invalid")
    status = "VERIFIED" if score >= float(shot.get("quality_targets", {}).get("audio_quality", 0.82)) and not errors else "REPAIR"
    return {"status": status, "score": score, "evidence": "provider",
            "checks": {"speaker_lock": bool(evidence.get("speaker") or evidence.get("identity") or shot.get("voice_prompt")),
                       "acoustic_continuity": bool(evidence.get("space") or evidence.get("world") or shot.get("sound_design_prompt")),
                       "motif_continuity": bool(evidence.get("motif") or memory.get("motifs") or shot.get("sound_design_prompt"))},
            "issues": errors}
