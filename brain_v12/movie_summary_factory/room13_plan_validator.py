#!/usr/bin/env python3
"""Stage 7 component 05: cinematic plan validator.

Validates the structural contract used by the Room 13 cinematic renderer.
The validator is intentionally dependency-free so CI can run it before
rendering. It returns structured errors and a non-zero exit code on failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = {
    "version", "title", "language", "target_minutes", "source_type",
    "beats", "shots",
}
REQUIRED_SHOT = {
    "id", "shot_type", "camera", "visual", "voice", "music", "sfx",
    "transition", "subtitle", "continuity", "duration_s",
}
REQUIRED_BEAT = {"id", "label", "rhythm"}


def validate_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = sorted(REQUIRED_TOP_LEVEL - set(plan))
    errors.extend(f"missing top-level field: {key}" for key in missing)

    if errors:
        return errors

    if not isinstance(plan["beats"], list) or not plan["beats"]:
        errors.append("beats must be a non-empty list")
    else:
        beat_ids: list[str] = []
        for index, beat in enumerate(plan["beats"], 1):
            if not isinstance(beat, dict):
                errors.append(f"beat {index} must be an object")
                continue
            missing_beat = REQUIRED_BEAT - set(beat)
            errors.extend(
                f"beat {index} missing field: {key}"
                for key in sorted(missing_beat)
            )
            if "id" in beat:
                beat_ids.append(str(beat["id"]))
        if len(beat_ids) != len(set(beat_ids)):
            errors.append("beat IDs must be unique")

    shots = plan["shots"]
    if not isinstance(shots, list) or not shots:
        errors.append("shots must be a non-empty list")
        return errors

    shot_ids: list[str] = []
    total_duration = 0.0
    for index, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            errors.append(f"shot {index} must be an object")
            continue
        missing_shot = REQUIRED_SHOT - set(shot)
        errors.extend(
            f"shot {index} missing field: {key}"
            for key in sorted(missing_shot)
        )
        shot_id = str(shot.get("id", ""))
        if shot_id:
            shot_ids.append(shot_id)
        try:
            duration = float(shot["duration_s"])
            if duration <= 0:
                errors.append(f"shot {index} duration_s must be > 0")
            total_duration += duration
        except (KeyError, TypeError, ValueError):
            errors.append(f"shot {index} duration_s must be numeric")

        for field in ("visual", "voice"):
            if not str(shot.get(field, "")).strip():
                errors.append(f"shot {index} {field} must not be empty")

        if shot_id and "-" in shot_id and plan["beats"]:
            beat_prefix = shot_id.split("-", 1)[0]
            known = {str(b.get("id")) for b in plan["beats"] if isinstance(b, dict)}
            if beat_prefix not in known:
                errors.append(f"shot {shot_id} references unknown beat {beat_prefix}")

    if len(shot_ids) != len(set(shot_ids)):
        errors.append("shot IDs must be unique")

    try:
        target_minutes = float(plan["target_minutes"])
        if target_minutes <= 0:
            errors.append("target_minutes must be > 0")
        else:
            target_seconds = target_minutes * 60.0
            tolerance = max(2.0, target_seconds * 0.02)
            if abs(total_duration - target_seconds) > tolerance:
                errors.append(
                    f"duration mismatch: shots={total_duration:.2f}s "
                    f"target={target_seconds:.2f}s tolerance={tolerance:.2f}s"
                )
    except (TypeError, ValueError):
        errors.append("target_minutes must be numeric")

    if plan.get("language") != "ar":
        errors.append("language must be 'ar' for the Room 13 Arabic pipeline")

    return errors


def validate_file(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    source = Path(path)
    plan = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        return {}, ["plan root must be a JSON object"]
    return plan, validate_plan(plan)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    path = Path(args[0]) if args else Path(
        "brain_v12/movie_summary_factory/jobs/room-13-horror-10m-cinematic-v3.json"
    )
    try:
        plan, errors = validate_file(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "status": "BLOCKED",
            "component": "Plan Validator",
            "path": str(path),
            "errors": [str(exc)],
        }, ensure_ascii=False, indent=2))
        return 2

    result = {
        "status": "READY" if not errors else "BLOCKED",
        "component": "Plan Validator",
        "component_id": 5,
        "path": str(path),
        "beats": len(plan.get("beats", [])),
        "shots": len(plan.get("shots", [])),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
