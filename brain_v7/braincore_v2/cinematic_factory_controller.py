"""End-to-end Cinematic Money Factory controller.

The controller is executable once real media and YouTube clients are injected.
It performs the full local workflow: topic selection -> cinematic plan ->
shot generation -> assembly -> YouTube package -> authorized publication ->
analytics ingestion -> next-video learning.

No credentials are stored here and no external side effect happens without
explicit authorization.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Protocol, Sequence
import time
from pathlib import Path

from .cinematic_money_factory import ContentOpportunity, rank
from .cinematic_director import CinematicPlan, build_plan, provider_prompts
from .youtube_publisher import YouTubePackage, prepare_package, publish
from .cinematic_story_engine import build_story
from .cinematic_quality_gate import inspect_video


class TopicResearcher(Protocol):
    def discover(self, *, audience: str, limit: int = 10) -> Sequence[dict[str, Any]]: ...


class ShotRenderer(Protocol):
    def render(self, *, shot: dict[str, Any], authorized: bool = False) -> dict[str, Any]: ...


class VideoAssembler(Protocol):
    def assemble(self, *, outputs: Sequence[dict[str, Any]], plan: CinematicPlan) -> dict[str, Any]: ...


class AnalyticsClient(Protocol):
    def report(self, *, video_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class FactoryConfig:
    audience: str = "Arabic-speaking YouTube audience"
    target_duration_s: int = 60
    minimum_quality: float = 0.82
    max_topics: int = 10
    publish_privacy: str = "private"


def choose_topic(researcher: TopicResearcher, config: FactoryConfig) -> dict[str, Any]:
    topics = list(researcher.discover(audience=config.audience, limit=config.max_topics))
    candidates: list[ContentOpportunity] = []
    for item in topics:
        candidates.append(ContentOpportunity(
            title=str(item.get("title", "Untitled")),
            objective=str(item.get("objective") or item.get("title") or ""),
            expected_value_jod=float(item.get("expected_value_jod", 0)),
            effort_hours=float(item.get("effort_hours", 2)),
            evidence=float(item.get("evidence", 0)),
            repeatability=float(item.get("repeatability", 0.5)),
            risk=float(item.get("risk", 0.5)),
            freshness=float(item.get("freshness", 0.5)),
            route=str(item.get("route", "youtube")),
        ))
    ranked = rank(candidates)
    return {
        "status": "TOPIC_SELECTED" if ranked else "NO_TOPIC",
        "selected": ranked[0] if ranked else None,
        "candidates": ranked,
    }


def build_production(objective: str, config: FactoryConfig) -> dict[str, Any]:
    plan = build_plan(
        objective,
        audience=config.audience,
        duration_s=config.target_duration_s,
    )
    return {
        "plan": plan,
        "shot_prompts": provider_prompts(plan),
    }


def render_shots(
    renderer: ShotRenderer,
    shot_prompts: Sequence[dict[str, Any]],
    *,
    authorized: bool = False,
) -> dict[str, Any]:
    outputs = []
    for shot in shot_prompts:
        result = renderer.render(shot=shot, authorized=authorized)
        if result.get("status") not in {"COMPLETED", "VERIFIED_COMPLETED"}:
            return {
                "status": "RENDER_BLOCKED",
                "failed_shot": shot.get("shot_id"),
                "outputs": outputs,
                "reason": result,
            }
        outputs.append(result)
    return {"status": "SHOTS_RENDERED", "outputs": outputs}


def run_factory(
    *,
    researcher: TopicResearcher,
    renderer: ShotRenderer,
    assembler: VideoAssembler,
    config: FactoryConfig = FactoryConfig(),
    youtube_client: Any = None,
    analytics_client: AnalyticsClient | None = None,
    authorized_production: bool = False,
    authorized_publish: bool = False,
    title: str | None = None,
    description: str = "",
    tags: Sequence[str] = (),
) -> dict[str, Any]:
    started = time.time()
    topic = choose_topic(researcher, config)
    if topic["status"] != "TOPIC_SELECTED":
        return {"status": "NO_TOPIC", "topic": topic}

    objective = topic["selected"]["opportunity"]["objective"]
    production = build_production(objective, config)
    story = build_story(objective, audience=config.audience)
    plan = production["plan"]

    if not authorized_production:
        return {
            "status": "PRODUCTION_AUTHORIZATION_REQUIRED",
            "topic": topic,
            "plan": asdict(plan),
            "story": story,
            "shot_prompts": production["shot_prompts"],
        }

    rendered = render_shots(renderer, production["shot_prompts"], authorized=True)
    if rendered["status"] != "SHOTS_RENDERED":
        return {"status": rendered["status"], "topic": topic, "render": rendered}

    assembled = assembler.assemble(outputs=rendered["outputs"], plan=plan)
    video_ref = assembled.get("video_ref")
    if not video_ref:
        return {
            "status": "ASSEMBLY_BLOCKED",
            "topic": topic,
            "render": rendered,
            "assembly": assembled,
        }

    quality = inspect_video(video_ref)
    if quality.get("status") != "ACCEPTED":
        return {
            "status": "QUALITY_GATE_BLOCKED",
            "topic": topic,
            "story": story,
            "render": rendered,
            "assembly": assembled,
            "quality": quality,
        }

    yt = prepare_package(
        title or objective[:90],
        description or f"فيديو سينمائي عن: {objective}",
        list(tags) or ["سينما", "محتوى عربي", "YouTube"],
        privacy=config.publish_privacy,
    )
    publication = publish(
        youtube_client,
        YouTubePackage(**yt["package"]),
        video_ref,
        authorized=authorized_publish,
    )

    analytics = None
    video_id = publication.get("provider_result", {}).get("video_id")
    if video_id and analytics_client:
        analytics = analytics_client.report(video_id=video_id)

    cleanup = None
    if publication.get("status") == "PUBLISHED":
        cleanup = cleanup_cycle_files(
            rendered_outputs=rendered["outputs"],
            final_video_ref=video_ref,
            keep_final=False,
        )

    return {
        "status": "FACTORY_CYCLE_COMPLETE",
        "elapsed_s": round(time.time() - started, 2),
        "topic": topic,
        "plan": asdict(plan),
        "story": story,
        "quality": quality,
        "rendered_shots": len(rendered["outputs"]),
        "assembly": assembled,
        "youtube": publication,
        "analytics": analytics,
        "cleanup": cleanup,
        "learning_input": {
            "next_cycle_required": True,
            "use_verified_analytics": analytics is not None,
            "do_not_infer_revenue": True,
        },
    }



def cleanup_cycle_files(*, rendered_outputs: Sequence[dict[str, Any]], final_video_ref: str | None, keep_final: bool = False) -> dict[str, Any]:
    """Delete only files created by the current factory cycle.

    Cleanup happens only after a successful YouTube publication. The uploaded
    YouTube copy remains the durable published artifact. Failed/unpublished
    cycles are intentionally left untouched for diagnosis or retry.
    """
    candidates: list[Path] = []
    for item in rendered_outputs:
        ref = item.get("video_ref")
        if ref and not str(ref).startswith(("http://", "https://")):
            candidates.append(Path(str(ref)))
    if final_video_ref and not str(final_video_ref).startswith(("http://", "https://")) and not keep_final:
        candidates.append(Path(str(final_video_ref)))

    removed_files = 0
    removed_dirs = 0
    errors: list[str] = []
    parent_dirs: set[Path] = set()
    for path in candidates:
        try:
            if path.is_file():
                path.unlink()
                removed_files += 1
                parent_dirs.add(path.parent)
        except OSError as exc:
            errors.append(f"{path}: {exc}")

    for directory in sorted(parent_dirs, key=lambda p: len(p.parts), reverse=True):
        if directory.name.startswith("factory_"):
            try:
                if directory.exists() and not any(directory.iterdir()):
                    directory.rmdir()
                    removed_dirs += 1
            except OSError as exc:
                errors.append(f"{directory}: {exc}")

    return {
        "status": "CLEANUP_COMPLETE" if not errors else "CLEANUP_PARTIAL",
        "removed_files": removed_files,
        "removed_dirs": removed_dirs,
        "errors": errors,
    }


def snapshot() -> dict[str, Any]:
    return {
        "topic_selection": True,
        "shot_generation": True,
        "video_assembly": True,
        "youtube_packaging": True,
        "authorized_publication": True,
        "analytics_feedback": True,
        "next_cycle_learning": True,
        "credentials_in_source": False,
        "guaranteed_revenue": False,
    }
