"""100-cycle self-healing controller for the Electronic Brain factory.

Each cycle:
1. reads the current error signal;
2. diagnoses the failure;
3. applies only deterministic, safe runtime repairs;
4. runs a lightweight health check;
5. records the result;
6. stops early only when health is verified.

It never marks a video successful merely because a repair was attempted.
"""
from __future__ import annotations
import json, os, shutil, subprocess, time
from pathlib import Path
from typing import Any

FAL_DEFAULT = "fal-ai/kling-video/v3/pro/text-to-video"
QUOTA_TOKENS = ("exhausted balance", "user is locked", "403 forbidden", "status_code=403")
MAX_CYCLES = 100

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

def health_check() -> dict[str, Any]:
    """Check runtime prerequisites without pretending that a film exists."""
    ffmpeg_bin = os.getenv("FFMPEG_BIN", "ffmpeg")
    try:
        p = subprocess.run([ffmpeg_bin, "-version"], capture_output=True, text=True, timeout=15)
        ffmpeg_ok = p.returncode == 0
    except Exception as exc:
        return {"healthy": False, "ffmpeg": False, "error": str(exc)}
    return {"healthy": ffmpeg_ok, "ffmpeg": ffmpeg_ok}

def repair_100_cycles(error_text: str = "", report_path: str = "factory_repair_100_report.json") -> dict[str, Any]:
    """Run up to 100 deterministic repair/health cycles."""
    history: list[dict[str, Any]] = []
    current_error = str(error_text or "")
    for cycle in range(1, MAX_CYCLES + 1):
        before = diagnose(current_error)
        result = repair(current_error)
        health = health_check()
        entry = {
            "cycle": cycle,
            "diagnosis": before,
            "repair_status": result["status"],
            "actions": result["actions"],
            "health": health,
        }
        history.append(entry)

        # A healthy runtime is not the same as a successfully rendered film.
        if health["healthy"] and before["recommended_route"] != "configuration_required":
            result = {
                "status": "RUNTIME_HEALTHY",
                "cycles_completed": cycle,
                "history": history,
                "note": "Film success still requires final.mp4 plus visual/audio/master QC.",
            }
            Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return result

        current_error = os.getenv("FACTORY_LAST_ERROR", current_error)
        time.sleep(float(os.getenv("FACTORY_REPAIR_DELAY_SECONDS", "0")))

    result = {
        "status": "REPAIR_LIMIT_REACHED",
        "cycles_completed": MAX_CYCLES,
        "history": history,
        "note": "No verified runtime recovery after 100 cycles; do not claim film success.",
    }
    Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

if __name__ == "__main__":
    supplied = os.getenv("FACTORY_LAST_ERROR", "")
    if os.getenv("FACTORY_REPAIR_100", "0").strip().lower() in {"1","true","yes","on"}:
        result = repair_100_cycles(supplied)
    else:
        result = repair(supplied)
    print(json.dumps(result, ensure_ascii=False))
    if result.get("status") == "REPAIR_LIMIT_REACHED":
        raise SystemExit(2)
