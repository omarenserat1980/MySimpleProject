"""Long-running cinematic factory worker.

All real external work is opt-in through environment configuration.
No credentials are stored in source. The worker emits auditable heartbeats
to stdout so Render logs can show liveness without exposing secrets.
"""
from __future__ import annotations
import json, os, time
from typing import Any
from .cinematic_factory_controller import run_factory, FactoryConfig
from .http_media_adapter import HttpShotRenderer, FfmpegVideoAssembler
from .cinematic_local_renderer import CinematicLocalRenderer
from .youtube_api_client import YouTubeApiClient
from .youtube_data_analytics_client import YouTubeDataAnalyticsClient
from .topic_sources import EnvTopicResearcher
from .worker_health import WorkerHealthRegistry
from .youtube_channel_control import YouTubeChannelControl

HEALTH = WorkerHealthRegistry(stale_after_s=180)
WORKER_ID = os.getenv("WORKER_ID", "brain-v7-autonomous")


def _truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _heartbeat(status: str, cycle: int, detail: str = "") -> None:
    beat = HEALTH.beat(WORKER_ID, status=status, cycle=cycle, detail=detail)
    print(json.dumps({"event": "WORKER_HEARTBEAT", **beat}, ensure_ascii=False, default=str), flush=True)


def _build_renderer():
    if os.getenv("MEDIA_RENDER_URL", "").strip():
        return HttpShotRenderer()
    return CinematicLocalRenderer()


def run_once(cycle: int = 0) -> dict[str, Any]:
    _heartbeat("HEALTHY", cycle, "starting_factory_cycle")
    cfg = FactoryConfig(
        audience=os.getenv("FACTORY_AUDIENCE", "Arabic-speaking YouTube audience"),
        target_duration_s=max(30, min(600, int(os.getenv("FACTORY_DURATION_SECONDS", "60")))),
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
    channel_snapshot = channel_control.channel() if channel_control else {"status": "YOUTUBE_NOT_CONFIGURED"}
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
    result["youtube_channel"] = channel_snapshot
    _heartbeat("HEALTHY", cycle, str(result.get("status", "cycle_complete")))
    print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
    return result


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
    run_forever()
