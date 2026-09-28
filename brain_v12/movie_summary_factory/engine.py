"""Movie Summary Factory orchestration.

Creates a deterministic production job from a movie title.  The factory produces
original summary/commentary assets and a shot-level plan; it does not reproduce
the movie's script or dialogue.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json, os, uuid

STAGES = [
    "SOURCE_PACK","STORY_EXTRACTION","CHARACTER_BIBLE","EVENT_GRAPH",
    "SUMMARY_SCRIPT","CINEMATIC_BEATS","SHOT_PLANNER","AUDIO_TIMELINE",
    "CONTINUITY_QC","VIDEO_RENDER"
]

@dataclass
class MovieSummaryJob:
    job_id: str
    title: str
    language: str
    target_minutes: int
    status: str
    stages: list
    script: str = ""
    output_url: str = ""

def create_job(title: str, target_minutes: int = 12, language: str = "ar") -> dict:
    if not title.strip():
        raise ValueError("MOVIE_TITLE_REQUIRED")
    if target_minutes not in (5, 8, 10, 12, 15, 20, 30):
        raise ValueError("UNSUPPORTED_TARGET_MINUTES")
    job = MovieSummaryJob(
        job_id=str(uuid.uuid4()),
        title=title.strip(),
        language=language,
        target_minutes=target_minutes,
        status="PLANNED",
        stages=[{"name": s, "status": "QUEUED"} for s in STAGES],
    )
    return asdict(job)

def mark_stage(job: dict, stage: str, status: str, **extra) -> dict:
    for item in job.get("stages", []):
        if item["name"] == stage:
            item["status"] = status
            item.update(extra)
            break
    job["status"] = "RUNNING" if status not in ("COMPLETED","FAILED") else job["status"]
    if all(x["status"] == "COMPLETED" for x in job.get("stages", [])):
        job["status"] = "COMPLETED"
    return job
