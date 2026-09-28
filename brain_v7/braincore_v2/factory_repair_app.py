"""Factory Repair App: diagnose and safely recover media-generation failures.

It does not fabricate provider success. It only changes local runtime routing:
- validates FFmpeg availability;
- detects known FAL quota/lock failures from supplied logs;
- enables the built-in FFmpeg fallback when configured;
- emits a machine-readable repair report.

Usage:
    python -m brain_v7.braincore_v2.factory_repair_app
"""
from __future__ import annotations
import json, os, shutil
from pathlib import Path
from typing import Any

FAL_DEFAULT = "fal-ai/kling-video/v3/pro/text-to-video"
QUOTA_TOKENS = ("exhausted balance", "user is locked", "403 forbidden", "status_code=403")

def diagnose(error_text: str = "") -> dict[str, Any]:
    text = str(error_text or "").lower()
    fal_key = bool(os.getenv("FAL_KEY", "").strip())
    fallback = os.getenv("FACTORY_ALLOW_LOCAL_FALLBACK", "0").strip().lower() in {"1","true","yes","on"}
    ffmpeg = shutil.which(os.getenv("FFMPEG_BIN", "ffmpeg")) is not None
    model = os.getenv("FAL_MODEL", "").strip() or FAL_DEFAULT
    quota = any(token in text for token in QUOTA_TOKENS)
    return {
        "fal_configured": fal_key,
        "fal_model": model,
        "fal_quota_blocked": quota,
        "local_fallback_enabled": fallback,
        "ffmpeg_available": ffmpeg,
        "recommended_route": "local_ffmpeg_cinematic" if quota and fallback and ffmpeg else (
            "fal" if fal_key else "local_ffmpeg_cinematic" if fallback and ffmpeg else "configuration_required"
        ),
    }

def repair(error_text: str = "", report_path: str = "factory_repair_report.json") -> dict[str, Any]:
    d = diagnose(error_text)
    actions: list[str] = []
    if not os.getenv("FAL_MODEL", "").strip():
        os.environ["FAL_MODEL"] = FAL_DEFAULT
        actions.append("resolved_empty_FAL_MODEL_to_known_default")
    if d["fal_quota_blocked"] and d["local_fallback_enabled"] and d["ffmpeg_available"]:
        os.environ["FACTORY_MEDIA_ROUTE"] = "local_ffmpeg_cinematic"
        actions.append("routed_FAL_quota_failure_to_local_ffmpeg_cinematic")
    result = {"status": "REPAIRED" if actions else "HEALTHY_OR_UNCHANGED",
              "diagnosis": d, "actions": actions}
    Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

if __name__ == "__main__":
    supplied = os.getenv("FACTORY_LAST_ERROR", "")
    result = repair(supplied)
    print(json.dumps(result, ensure_ascii=False))
    if result["diagnosis"]["recommended_route"] == "configuration_required":
        raise SystemExit(2)
