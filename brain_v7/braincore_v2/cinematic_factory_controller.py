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
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .cinematic_money_factory import ContentOpportunity, rank
from .reference_engine import build_reference_manifest
from .visual_qc import inspect_shot
from .continuity_ledger import ContinuityLedger
from .cinematic_director import CinematicPlan, build_plan, provider_prompts
from .youtube_publisher import YouTubePackage, prepare_package, publish
from .cinematic_story_engine import build_story
from .story_architect import build_story as build_executable_story, export_story
from .film_memory import FilmMemory
from .film_qc import evaluate_film_evidence
from .repair_planner import build_repairs
from .production_memory import ProductionMemory
from .director_scheduler import seed_tasks, choose_next
from .task_stack import TaskStack
from .final_film_qc import evaluate_final_film
from .cinematic_quality_gate import inspect_video
from .audio_continuity import AudioContinuity
from .audio_qc import evaluate_audio_evidence
from .research_ledger import ResearchLedger
from .research_gate import evaluate_research_gate
from .self_improvement import SelfImprovement
from .production_diagnostics import diagnose
from .mastering_qc import evaluate_master
from .brain_media_adapter import FactoryState
from .speed_optimizer import speed_policy, apply_speed_policy
from .take_budget import take_budget
from .production_speed_optimizer import speed_plan
from .throughput_metrics import measure, snapshot as throughput_snapshot


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


def render_shots(renderer: ShotRenderer, shot_prompts: Sequence[dict[str, Any]], *, authorized: bool = False, state_path: str = ".factory_state.json") -> dict[str, Any]:
    """Render independent shots concurrently with isolated retries and checkpoints."""
    state = FactoryState(state_path)
    ledger = ContinuityLedger(Path(state_path).with_name("continuity_ledger.json").as_posix())
    memory = FilmMemory(Path(state_path).with_name("film_memory.json").as_posix())
    production_memory = ProductionMemory(Path(state_path).parent.as_posix())
    audio_memory = AudioContinuity(Path(state_path).with_name("audio_continuity.json").as_posix())
    research_ledger = ResearchLedger(Path(state_path).with_name("research_ledger.json").as_posix())
    self_improvement = SelfImprovement(Path(state_path).with_name("production_policy.json").as_posix())
    require_audio_evidence = os.getenv("FACTORY_REQUIRE_AUDIO_EVIDENCE", "0").lower() in {"1", "true", "yes", "on"}
    max_retries = max(0, int(os.getenv("FACTORY_SHOT_RETRIES", "2")))
    speed = speed_policy()
    concurrency = speed["concurrency"]
    throughput_plan = speed_plan(list(shot_prompts), max_concurrency=concurrency)
    lock = threading.Lock()
    pending, outputs, failures = [], [], []
    skipped = 0

    for index, original in enumerate(shot_prompts, 1):
        shot = dict(original)
        shot_id = str(shot.get("shot_id") or f"shot_{index:04d}")
        cached = state.verified(shot_id)
        if cached:
            outputs.append(cached); skipped += 1; continue
        shot = apply_speed_policy(shot)
        shot["continuity_dna"] = {
            "continuity_key": shot.get("continuity_key", ""),
            "identity_lock": "preserve subject appearance, wardrobe, proportions and visual identity",
            "world_lock": "preserve geography, time of day, weather, architecture and color language",
            "camera_lock": "preserve lens, framing and motivated camera movement",
        }
        shot["reference_manifest"] = build_reference_manifest(
            {"character_bible": shot.get("character_bible", {}), "world_bible": shot.get("world_bible", {})},
            (Path(state_path).parent / "references" / shot_id).as_posix(),
        )
        pending.append((shot_id, shot))

    def render_one(shot_id, shot):
        result = None
        budget = take_budget(shot)
        attempts_allowed = min(max_retries + 1, int(budget["max_takes"]))
        for attempt in range(attempts_allowed):
            with measure("generation", path=Path(state_path).with_name("factory_throughput.json")):
                result = renderer.render(shot=shot, authorized=authorized)
            if result.get("status") in {"COMPLETED", "VERIFIED_COMPLETED"}:
                result["attempt"] = attempt + 1
                with measure("visual_qc", path=Path(state_path).with_name("factory_throughput.json")):
                    qc = inspect_shot(shot, result, min_score=float(os.getenv("FACTORY_MIN_QUALITY", "0.82")))
                result["visual_qc"] = qc
                result["audio_qc"] = evaluate_audio_evidence(shot, result, audio_memory.context())
                result["research_qc"] = evaluate_research_gate(shot, result, research_ledger.items)
                result["film_qc"] = evaluate_film_evidence(shot, result, memory.snapshot())
                if require_audio_evidence and result["audio_qc"]["status"] != "VERIFIED":
                    result["film_qc"]["status"] = "REPAIR"
                    result["film_qc"].setdefault("issues", []).append("audio_qc_not_verified")
                if result["research_qc"]["status"] != "VERIFIED":
                    result["film_qc"]["status"] = "REPAIR"
                    result["film_qc"].setdefault("issues", []).append("research_gate_blocked")
                result["repair_plan"] = build_repairs(result["film_qc"], shot)
                result["throughput"] = throughput_snapshot(Path(state_path).with_name("factory_throughput.json"))
                result["take_budget"] = budget
                self_improvement.observe(shot_id, result)
                audio_memory.update(shot_id, {"voice_prompt": shot.get("voice_prompt"), "sound_design_prompt": shot.get("sound_design_prompt"), "qc": result["audio_qc"]})
                if qc["status"] == "VERIFIED" and result["film_qc"]["status"] == "VERIFIED":
                    ledger.record(shot_id, scene_id=shot.get("scene_id"), continuity_key=shot.get("continuity_key"), qc=qc, attempt=attempt + 1)
                    result["status"] = "VERIFIED_COMPLETED"
                    break
                result["status"] = "QC_REJECTED"
                shot["retry_context"] = "Visual QC rejected attempt %d: %s" % (attempt + 1, qc.get("errors", []))
            else:
                shot["retry_context"] = f"Previous attempt failed: {result.get('status')}. Improve validity and prompt adherence."
        final = result or {"status": "PROVIDER_ERROR"}
        with lock:
            state.save(shot_id, final)
        return shot_id, final

    pending_map = {shot_id: shot for shot_id, shot in pending}
    task_stack = seed_tasks(TaskStack(Path(state_path).with_name("task_stack.json").as_posix()), list(pending_map.values()))
    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="factory-shot") as pool:
        while True:
            ready = [t for t in task_stack.ready() if t["task_id"] in pending_map]
            if not ready: break
            futures = [pool.submit(render_one, t["task_id"], pending_map[t["task_id"]]) for t in ready]
            for t, future in zip(ready, futures):
                shot_id, result = future.result()
                if result.get("status") == "VERIFIED_COMPLETED":
                    with lock:
                        memory.update_shot(shot_id, {"continuity_key": result.get("continuity_key"), "visual_qc": result.get("visual_qc"), "audio_qc": result.get("audio_qc"), "research_qc": result.get("research_qc"), "film_qc": result.get("film_qc"), "repair_plan": result.get("repair_plan"), "video_ref": result.get("video_ref")})
                        production_memory.commit_evidence(shot_id, {"visual_qc": result.get("visual_qc"), "audio_qc": result.get("audio_qc"), "research_qc": result.get("research_qc"), "film_qc": result.get("film_qc"), "video_ref": result.get("video_ref")})
                    outputs.append(result); task_stack.complete(shot_id)
                else:
                    failures.append({"shot_id": shot_id, "result": result}); task_stack.fail(shot_id, result.get("repair_plan"))
            if failures: break

    outputs.sort(key=lambda x: str(x.get("shot_id", "")))
    diagnostics = diagnose({"status": "SHOTS_BLOCKED" if failures else "VERIFIED_COMPLETED", "visual_qc": outputs[-1].get("visual_qc") if outputs else {}, "film_qc": outputs[-1].get("film_qc") if outputs else {}})
    if failures:
        manifest = {"version": 5, "status": "SHOTS_BLOCKED", "speed_plan": throughput_plan, "throughput_metrics": throughput_snapshot(Path(state_path).with_name("factory_throughput.json")), "shot_count": len(outputs), "skipped_verified": skipped, "failed_shots": failures, "shots": outputs, "diagnostics": diagnostics, "production_policy": self_improvement.context(), "audio_continuity": audio_memory.context(), "updated_at": time.time()}
        Path(state_path).with_name("cinematic_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return {"status": "SHOTS_BLOCKED", "failed_shot": failures[0]["shot_id"], "outputs": outputs, "skipped": skipped, "failures": failures, "manifest": manifest}

    manifest = {"version": 6, "status": "SHOTS_RENDERED", "speed_plan": throughput_plan, "throughput_metrics": throughput_snapshot(Path(state_path).with_name("factory_throughput.json")), "shot_count": len(outputs), "skipped_verified": skipped, "shots": outputs, "diagnostics": diagnostics, "production_policy": self_improvement.context(), "audio_continuity": audio_memory.context(), "updated_at": time.time()}
    Path(state_path).with_name("cinematic_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"status": "SHOTS_RENDERED", "outputs": outputs, "skipped": skipped, "manifest": manifest}


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
    executable_story = build_executable_story(objective, genre=str(production["plan"].creative_contract.get("genre", "cinematic") if production["plan"].creative_contract else "cinematic"))
    plan = production["plan"]
    Path(os.getenv("FACTORY_PROJECT_MANIFEST", "cinematic_project_manifest.json")).write_text(
        json.dumps({"plan": asdict(plan), "story": story, "executable_story": export_story(executable_story), "shot_prompts": production["shot_prompts"], "created_at": time.time()},
                   ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    if not authorized_production:
        return {
            "status": "PRODUCTION_AUTHORIZATION_REQUIRED",
            "topic": topic,
            "plan": asdict(plan),
            "story": story,
            "executable_story": export_story(executable_story),
            "shot_prompts": production["shot_prompts"],
        }

    task_stack = seed_tasks(TaskStack(Path(os.getenv("FACTORY_STATE_PATH", ".factory_state.json")).with_name("task_stack.json").as_posix()), production["shot_prompts"])
    dispatch_preview = choose_next(task_stack, {"factory":"cinematic","objective":objective})
    rendered = render_shots(renderer, production["shot_prompts"], authorized=True, state_path=os.getenv("FACTORY_STATE_PATH", ".factory_state.json"))
    if rendered["status"] != "SHOTS_RENDERED":
        return {"status": rendered["status"], "topic": topic, "render": rendered}

    final_qc = evaluate_final_film(rendered["manifest"], rendered["outputs"])
    if final_qc.get("status") != "VERIFIED":
        return {"status":"FINAL_FILM_QC_BLOCKED","topic":topic,"render":rendered,"final_qc":final_qc,"dispatch":dispatch_preview}
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
    mastering = evaluate_master(video_ref, len(rendered["outputs"]), manifest=rendered.get("manifest"))
    if quality.get("status") != "ACCEPTED" or mastering.get("status") != "VERIFIED":
        return {
            "status": "QUALITY_GATE_BLOCKED",
            "topic": topic,
            "story": story,
            "executable_story": export_story(executable_story),
            "render": rendered,
            "assembly": assembled,
            "quality": quality,
            "mastering_qc": mastering,
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
        "executable_story": export_story(executable_story),
        "quality": quality,
        "mastering_qc": mastering,
        "rendered_shots": len(rendered["outputs"]),
        "skipped_verified_shots": rendered.get("skipped", 0),
        "manifest": rendered.get("manifest"),
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
        "creative_council": True,
        "film_dsl": True,
        "story_architecture": True,
        "persistent_film_memory": True,
        "persistent_world_state": True,
        "targeted_repair_planner": True,
        "evidence_feedback_to_next_shot": True,
        "multi_dimensional_qc": True,
        "research_ledger": True,
        "closed_loop_repair": True,
        "next_cycle_learning": True,
        "audio_continuity": True,
        "audio_qc": True,
        "research_gate": True,
        "adaptive_policy": True,
        "production_diagnostics": True,
        "mastering_qc": True,
        "credentials_in_source": False,
        "guaranteed_revenue": False,
    }
