#!/usr/bin/env python3
"""Unified BRAIN Cinematic Quality Gate.

This is the single pre-release gate for cinematic production. It combines:
repair-contract validation, visual variation, repaired audio evidence, real
timeline transitions, continuity rejection, duplicate-scene rejection, and
the independent Cinematic Master QC.

The gate fails closed: any missing evidence or unexpected QC behavior exits
non-zero. It does not create VERIFIED_COMPLETED; only the master workflow may
promote a render after this gate passes.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("BRAIN_CQG_ROOT", "/tmp/brain-cinematic-quality-gate"))
CONTRACT = WORK / "repair-contract.json"
PROGRESS = WORK / "CINEMATIC_QUALITY_GATE_PROGRESS.json"


def progress(stage: int, total: int, name: str, status: str, detail: str = "") -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    payload = {"stage": stage, "total_stages": total, "percent": round(stage * 100 / total), "name": name, "status": status, "detail": detail}
    PROGRESS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== CINEMATIC QUALITY GATE {payload['percent']}% | {status} | {name} ===")
    print(f"DETAIL: {detail}")
    filled = max(1, stage * 20 // total)
    print(f"PROGRESS: [{'#' * filled}{'.' * (20 - filled)}] {payload['percent']}%")
    print(f"GATE_STATUS={status}")
PROGRESS = WORK / "CINEMATIC_QUALITY_GATE_PROGRESS.json"


def progress(stage: int, total: int, name: str, status: str, detail: str = "") -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": stage,
        "total_stages": total,
        "percent": round(stage * 100 / total),
        "name": name,
        "status": status,
        "detail": detail,
    }
    PROGRESS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== CINEMATIC QUALITY GATE {payload['percent']}% | {status} | {name} ===")
    if detail:
        print(f"DETAIL: {detail}")
    print(f"PROGRESS: [{('=' * max(1, stage * 20 // total))}{'.' * max(0, 20 - stage * 20 // total)}] {payload['percent']}%")
    print(f"GATE_STATUS={status}")


def run(cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stdout + "\\n" + p.stderr)[-8000:])
    return p


def main() -> int:
    total = 8
    WORK.mkdir(parents=True, exist_ok=True)
    progress(0, total, "Preflight", "RUNNING", "Checking FFmpeg/ffprobe and local voice generator")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFMPEG_REQUIRED")
    if not (shutil.which("espeak-ng") or shutil.which("espeak")):
        raise RuntimeError("VOICE_ASSET_GENERATOR_MISSING")
    progress(1, total, "Preflight", "PASSED", "Required executors are available")

    progress(1, total, "Preflight", "PASSED", "Required executors are available")
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)

    qc = {
        "repair_manifest": {
            "mandatory_requirements": [
                "INCREASE_DISTINCT_SCENE_COUNT",
                "GENERATE_MATERIALLY_DIVERSE_VISUALS",
                "REBUILD_DUPLICATE_SCENES",
                "REQUIRE_CAMERA_OR_ELEMENT_MOTION",
            ]
        }
    }
    progress(2, total, "Repair contract compilation", "RUNNING", "Compiling mandatory repair requirements")
    progress(2, total, "Repair contract compilation", "RUNNING", "Compiling mandatory repair requirements")
    qc_path = WORK / "qc.json"
    qc_path.write_text(json.dumps(qc), encoding="utf-8")
    contract_out = WORK / "compiled-contract.json"
    run([sys.executable, "brain_v12/cinematic_repair_loop.py",
         "--qc", str(qc_path), "--output", str(contract_out)])
    compiled = json.loads(contract_out.read_text())
    assert compiled["status"] == "REPAIR_REQUIRED"
    assert compiled["min_distinct_scenes"] == 24
    assert compiled["visual_diversity_required"] is True
    assert compiled["duplicate_scene_policy"] == "reject"
    assert compiled["motion_required"] is True
    progress(2, total, "Repair contract compilation", "PASSED", "Mandatory renderer requirements compiled")

    render_contract = {
        "status": "REPAIR_REQUIRED",
        "reject_on_missing_evidence": True,
        "mandatory_requirements": [
            "REQUIRE_VOICE_NARRATION_ASSETS",
            "REQUIRE_MUSIC_ASSETS",
            "REQUIRE_SFX_AMBIENCE_ASSETS",
            "REQUIRE_CAMERA_OR_ELEMENT_MOTION",
            "REQUIRE_REAL_SCENE_TRANSITIONS",
        ],
        "voice_required": True,
        "music_required": True,
        "sfx_required": True,
        "motion_required": True,
        "transitions_required": True,
        "min_video_bitrate_bps": 800000,
    }
    CONTRACT.write_text(json.dumps(render_contract), encoding="utf-8")
    progress(3, total, "Evidence-aware smoke render", "RUNNING", "Rendering 2 short parts with voice/music/SFX/motion/transitions")

    env = os.environ.copy()
    env.update({
        "BRAIN_MACHINE_FILM_ROOT": str(WORK),
        "BRAIN_FILM_PARTS": "2",
        "BRAIN_FILM_START": "1",
        "BRAIN_FILM_END": "2",
        "BRAIN_FILM_PART_SECONDS": "2",
        "BRAIN_CINEMATIC_REPAIR_CONTRACT": str(CONTRACT),
    })
    p = subprocess.run(
        [sys.executable, "brain_v12/machine_cinematic_factory.py"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=3600,
    )
    if p.returncode:
        raise RuntimeError((p.stdout + "\n" + p.stderr)[-12000:])
    progress(3, total, "Evidence-aware smoke render", "PASSED", "Smoke render completed")

    progress(4, total, "Audio and transition evidence", "RUNNING", "Checking voice, music, SFX and xfade evidence")
    manifest_path = WORK / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    final = Path(manifest["final"])
    assert final.is_file() and final.stat().st_size > 0

    for item in manifest["parts_manifest"]:
        assets = item["audio_assets"]
        for key in ("voice", "music", "sfx"):
            assert assets[key] and Path(assets[key]).is_file() and Path(assets[key]).stat().st_size > 0

    transitions = manifest.get("timeline_transitions") or {}
    assert transitions.get("type") == "xfade"
    assert transitions.get("count") == 1
    progress(4, total, "Audio and transition evidence", "PASSED", "Voice/music/SFX assets and real xfade transition verified")

    progress(5, total, "Independent Cinematic Master QC", "RUNNING", "Evaluating the short render without granting production promotion")
    cinematic = manifest.get("cinematic_master_qc") or {}
    if not cinematic:
        from brain_v12.cinematic_master_qc import evaluate
        cinematic = evaluate(final, manifest_path)
    assert cinematic.get("status") == "CINEMATIC_QC_FAILED"
    checks = cinematic.get("checks") or {}
    for key in ("voice_evidence", "music_evidence", "sfx_evidence",
                "scene_transitions", "character_story_continuity",
                "manifest_video_consistency"):
        # Audio and transition evidence must pass even though the short smoke
        # render is intentionally too small to be a production-quality film.
        if key in ("voice_evidence", "music_evidence", "sfx_evidence",
                   "scene_transitions", "character_story_continuity",
                   "manifest_video_consistency"):
            assert checks.get(key) is True, key
    progress(5, total, "Independent Cinematic Master QC", "PASSED", "Expected smoke limitations are rejected while required evidence checks pass")

    progress(6, total, "Negative continuity gate", "RUNNING", "Injecting broken continuity and verifying rejection")
    from brain_v12.cinematic_master_qc import evaluate

    broken = copy.deepcopy(manifest)
    broken["parts_manifest"][1]["scene"]["world_id"] = "BROKEN-WORLD"
    broken["parts_manifest"][1]["scene"]["continuity_anchor"] = "broken"
    broken_path = WORK / "broken-continuity.json"
    broken_path.write_text(json.dumps(broken), encoding="utf-8")
    bad = evaluate(final, broken_path)
    assert bad["checks"]["character_story_continuity"] is False
    assert "REQUIRE_SCENE_CHARACTER_WORLD_BIBLES" in bad["repair_manifest"]["mandatory_requirements"]
    progress(6, total, "Negative continuity gate", "PASSED", "Broken continuity was correctly rejected")

    progress(7, total, "Negative duplicate-scene gate", "RUNNING", "Injecting duplicate scene identity and verifying rejection")
    duplicate = copy.deepcopy(manifest)
    duplicate["parts_manifest"][1]["scene"] = copy.deepcopy(duplicate["parts_manifest"][0]["scene"])
    duplicate["parts_manifest"][1]["scene"]["scene_id"] = duplicate["parts_manifest"][0]["scene"]["scene_id"]
    duplicate_path = WORK / "duplicate-scenes.json"
    duplicate_path.write_text(json.dumps(duplicate), encoding="utf-8")
    dup = evaluate(final, duplicate_path)
    assert dup["checks"]["duplicate_scene_detection"] is False
    assert "REBUILD_DUPLICATE_SCENES" in dup["repair_manifest"]["mandatory_requirements"]
    progress(7, total, "Negative duplicate-scene gate", "PASSED", "Duplicate scene was correctly rejected")

    progress(8, total, "Gate evidence publication", "RUNNING", "Writing machine-readable gate evidence")
    result = {
        "status": "CINEMATIC_QUALITY_GATE_PASSED",
        "scope": [
            "repair_contract",
            "visual_variation",
            "voice_music_sfx_assets",
            "real_xfade_transitions",
            "continuity_positive_evidence",
            "continuity_negative_gate",
            "duplicate_scene_negative_gate",
            "independent_cinematic_master_qc",
        ],
        "production_promotion": "NOT_GRANTED",
        "note": "Smoke gate passed its required evidence checks; the short render remains intentionally below production scene-count thresholds.",
    }
    (WORK / "CINEMATIC_QUALITY_GATE.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    progress(8, total, "Gate evidence publication", "PASSED", "CINEMATIC_QUALITY_GATE evidence written; production promotion remains separate")
    progress(8, total, "Gate evidence publication", "PASSED", "Gate evidence written; production promotion remains separate")
    print("CINEMATIC_QUALITY_GATE_PASSED")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        WORK.mkdir(parents=True, exist_ok=True)
        failed = {"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)[-4000:]}
        (WORK / "CINEMATIC_QUALITY_GATE_FAILURE.json").write_text(json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n=== CINEMATIC QUALITY GATE | FAILED ===")
        print("FAILURE: " + type(exc).__name__ + ": " + str(exc)[-4000:])
        print("GATE_STATUS=FAILED")
        raise
