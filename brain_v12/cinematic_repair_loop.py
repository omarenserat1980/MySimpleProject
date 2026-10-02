#!/usr/bin/env python3
"""Deterministic repair-contract compiler for Brain cinematic production.

Consumes cinematic_master_qc.json and produces a renderer-facing contract.
No requirement is silently dropped.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

MAP = {
 "INCREASE_DISTINCT_SCENE_COUNT": {"min_distinct_scenes": 24},
 "GENERATE_MATERIALLY_DIVERSE_VISUALS": {"visual_diversity_required": True},
 "REQUIRE_REAL_IMAGE_OR_DRAWING_ASSETS": {"image_assets_required": True},
 "REQUIRE_CAMERA_OR_ELEMENT_MOTION": {"motion_required": True},
 "REQUIRE_REAL_SCENE_TRANSITIONS": {"transitions_required": True},
 "REQUIRE_SCENE_CHARACTER_WORLD_BIBLES": {"continuity_required": True},
 "REQUIRE_VOICE_NARRATION_ASSETS": {"voice_required": True},
 "REQUIRE_MUSIC_ASSETS": {"music_required": True},
 "REQUIRE_SFX_AMBIENCE_ASSETS": {"sfx_required": True},
 "REBUILD_REPEATED_TONE_AUDIO": {"audio_diversity_required": True},
 "REPLACE_BLACK_SEGMENTS": {"black_frame_repair_required": True},
 "REBUILD_FROZEN_SEGMENTS": {"frozen_frame_repair_required": True},
 "REBUILD_DUPLICATE_SCENES": {"duplicate_scene_policy": "reject"},
 "REMOVE_UNINTENDED_TEXT_OVERLAYS": {"unintended_text_forbidden": True},
 "INCREASE_VIDEO_ENCODING_QUALITY": {"min_video_bitrate_bps": 800000},
 "REPAIR_MANIFEST_RENDER_ALIGNMENT": {"manifest_alignment_required": True},
}

def compile_contract(qc: dict) -> dict:
    reqs = (qc.get("repair_manifest") or {}).get("mandatory_requirements", [])
    contract = {"status": "REPAIR_REQUIRED" if reqs else "NO_REPAIR_REQUIRED",
                "reject_on_missing_evidence": True,
                "mandatory_requirements": reqs}
    for req in reqs:
        contract.update(MAP.get(req, {}))
    return contract

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--qc",required=True)
    ap.add_argument("--output",default="cinematic_repair_contract.json")
    a=ap.parse_args()
    qc=json.loads(Path(a.qc).read_text(encoding="utf-8"))
    contract=compile_contract(qc)
    Path(a.output).write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(contract,ensure_ascii=False,indent=2))
    # A repair contract is an actionable artifact; its existence must never
    # be interpreted as permission to promote the current render.
    return 0

if __name__=="__main__":
 raise SystemExit(main())
