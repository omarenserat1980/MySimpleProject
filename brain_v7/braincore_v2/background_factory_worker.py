"""Long-running cinematic factory worker.

All real external work is opt-in through environment configuration.
No credentials are stored here. The worker emits auditable heartbeats.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

from .cinematic_factory_controller import run_factory, FactoryConfig
from .http_media_adapter import FfmpegVideoAssembler
from .brain_media_adapter import BrainMediaProvider
from .cinema_engine_v6 import CinemaEngineV6
from .cinema_manifest import write_manifest
from .model_router import ModelRouter
from .youtube_api_client import YouTubeApiClient
from .youtube_data_analytics_client import YouTubeDataAnalyticsClient
from .topic_sources import EnvTopicResearcher
from .worker_health import WorkerHealthRegistry
from .youtube_channel_control import YouTubeChannelControl
from .brain_orchestrator import UnifiedBrain

HEALTH = WorkerHealthRegistry(stale_after_s=180)
WORKER_ID = os.getenv("WORKER_ID", "brain-v7-autonomous")


def _truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _heartbeat(status: str, cycle: int, detail: str = "") -> None:
    beat = HEALTH.beat(WORKER_ID, status=status, cycle=cycle, detail=detail)
    print(json.dumps({"event": "WORKER_HEARTBEAT", **beat}, ensure_ascii=False, default=str), flush=True)


def _build_renderer():
    # Production must never silently downgrade to the FFmpeg-only local renderer.
    # A missing real media backend is a hard configuration error.
    has_real_provider = bool(
        os.getenv("FAL_KEY", "").strip()
        or os.getenv("MEDIA_PROVIDER_URL", "").strip()
        or os.getenv("COMFYUI_URL", "").strip()
    )
    allow_local = _truthy("FACTORY_ALLOW_LOCAL_FALLBACK", "0") and not _truthy(
        "FACTORY_ALLOW_PRODUCTION", "0"
    )
    if not has_real_provider and not allow_local:
        raise RuntimeError(
            "REAL_MEDIA_PROVIDER_REQUIRED: configure FAL_KEY, MEDIA_PROVIDER_URL, "
            "or COMFYUI_URL; local FFmpeg fallback is disabled for production."
        )
    fallback = BrainMediaProvider()
    if _truthy("FACTORY_MODEL_ROUTER", "1"):
        return ModelRouter(fallback)
    return fallback


def run_once(cycle: int = 0) -> dict[str, Any]:
    _heartbeat("HEALTHY", cycle, "starting_factory_cycle")
    write_manifest(os.getenv("CINEMA_ENGINE_MANIFEST", "cinema_engine_v6_manifest.json"))
    cfg = FactoryConfig(
        audience=os.getenv("FACTORY_AUDIENCE", "Arabic-speaking YouTube audience"),
        target_duration_s=max(1, min(600, int(os.getenv("FACTORY_DURATION_SECONDS", "60")))),
        minimum_quality=float(os.getenv("FACTORY_MIN_QUALITY", "0.82")),
        max_topics=max(1, min(50, int(os.getenv("FACTORY_MAX_TOPICS", "10")))),
        publish_privacy=os.getenv("YOUTUBE_PRIVACY", "private"),
    )
    researcher = EnvTopicResearcher()
    renderer = _build_renderer()
    assembler = FfmpegVideoAssembler()
    yt = YouTubeApiClient() if os.getenv("YOUTUBE_REFRESH_TOKEN") else None
    analytics = YouTubeDataAnalyticsClient() if yt else None
    channel_control = YouTubeChannelControl() if yt else None
    oauth_snapshot = {"status": "YOUTUBE_NOT_CONFIGURED"}
    if yt:
        oauth_snapshot = yt.validate()
        if oauth_snapshot.get("status") != "OAUTH_VALID":
            _heartbeat("DEGRADED", cycle, f"youtube_oauth={oauth_snapshot.get('code', 'invalid')}")
            yt = None
            analytics = None
            channel_control = None
    channel_snapshot = channel_control.channel() if channel_control else oauth_snapshot
    result = run_factory(
        researcher=researcher,
        renderer=renderer,
        assembler=assembler,
        config=cfg,
        youtube_client=yt,
        analytics_client=analytics,
        authorized_production=_truthy("FACTORY_ALLOW_PRODUCTION"),
        authorized_publish=_truthy("FACTORY_ALLOW_YOUTUBE_PUBLISH"),
        description=os.getenv("YOUTUBE_DESCRIPTION", ""),
        tags=[x.strip() for x in os.getenv("YOUTUBE_TAGS", "سينما,محتوى عربي,YouTube").split(",") if x.strip()],
    )
    result["youtube_oauth"] = oauth_snapshot
    result["youtube_channel"] = channel_snapshot
    if hasattr(renderer, "snapshot"):
        result["model_router"] = renderer.snapshot()
    result["cinema_engine"] = CinemaEngineV6().snapshot()
    final_status = "DEGRADED" if oauth_snapshot.get("status") == "OAUTH_INVALID" else "HEALTHY"
    final_detail = str(result.get("status", "cycle_complete"))
    if oauth_snapshot.get("status") == "OAUTH_INVALID":
        final_detail = f"{final_detail};youtube_oauth={oauth_snapshot.get('code', 'invalid')}"
    _heartbeat(final_status, cycle, final_detail)
    print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
    return result


def run_autonomous_cycle(cycle: int = 1) -> dict[str, Any]:
    """Brain-first factory loop with both attempt and wall-clock limits."""
    max_attempts = max(1, min(1000, int(os.getenv("BRAIN_MAX_ITERATIONS", "1000"))))
    max_runtime_s = max(60, min(6 * 60 * 60, int(os.getenv("BRAIN_MAX_RUNTIME_SECONDS", "21600"))))
    started = time.time()
    brain = UnifiedBrain()
    last: dict[str, Any] = {}
    for attempt in range(1, max_attempts + 1):
        if time.time() - started >= max_runtime_s:
            break
        _heartbeat("AUTONOMOUS_ATTEMPT", cycle, f"attempt={attempt}/{max_attempts}")
        try:
            result = run_once(cycle)
            last = result
            status = str(result.get("status", "")).upper()
            if status in {"COMPLETED", "VERIFIED", "SUCCESS", "FACTORY_CYCLE_COMPLETE"}:
                result["brain_autonomy"] = {"attempt": attempt, "max_attempts": max_attempts, "status": "SUCCESS"}
                return result

            diagnosis = brain.cycle(
                os.getenv("FACTORY_OBJECTIVE", "Produce and verify the cinematic film"),
                outcome="failure",
                outcome_evidence=json.dumps(result, ensure_ascii=False, default=str)[:6000],
            )
            print(json.dumps({
                "event": "BRAIN_REPLAN",
                "attempt": attempt,
                "max_attempts": max_attempts,
                "diagnosis": diagnosis.get("selected_internal_focus"),
                "result_status": status,
            }, ensure_ascii=False, default=str), flush=True)
        except Exception as exc:
            last = {"status": "FACTORY_ERROR", "error": repr(exc)}
            diagnosis = brain.cycle(
                os.getenv("FACTORY_OBJECTIVE", "Produce and verify the cinematic film"),
                outcome="failure",
                outcome_evidence=repr(exc),
            )
            print(json.dumps({
                "event": "BRAIN_REPLAN",
                "attempt": attempt,
                "max_attempts": max_attempts,
                "error": repr(exc),
                "diagnosis": diagnosis.get("selected_internal_focus"),
            }, ensure_ascii=False, default=str), flush=True)

    last["status"] = "MAX_ITERATIONS"
    last["brain_autonomy"] = {
        "attempt": min(max_attempts, attempt if "attempt" in locals() else max_attempts),
        "max_attempts": max_attempts,
        "runtime_seconds": round(time.time() - started, 1),
        "max_runtime_seconds": max_runtime_s,
        "status": "ESCALATE_TO_USER",
        "reason": "autonomous Brain budget exhausted (attempts or wall-clock limit) without verified success",
    }
    _heartbeat("ESCALATE", cycle, f"max_attempts={max_attempts}")
    print(json.dumps(last, ensure_ascii=False, default=str), flush=True)
    return last


def run_forever() -> None:
    interval = max(60, int(os.getenv("FACTORY_INTERVAL_SECONDS", "21600")))
    cycle = 0
    while not _truthy("STOP_BRAIN"):
        cycle += 1
        try:
            run_once(cycle)
        except Exception as exc:
            _heartbeat("ERROR", cycle, repr(exc))
            print(json.dumps({"status": "FACTORY_ERROR", "error": repr(exc)}, ensure_ascii=False), flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    # GitHub Actions is finite; run one production cycle there.
    if _truthy("FACTORY_ONE_SHOT", "0"):
        result = run_autonomous_cycle(1)
        # GitHub Actions must not report a green production when the factory
        # stopped before rendering/assembling the requested film.
        status = str(result.get("status", ""))
        if status not in {"COMPLETED", "VERIFIED", "SUCCESS", "FACTORY_CYCLE_COMPLETE"}:
            raise SystemExit(2)
    else:
        run_forever()
