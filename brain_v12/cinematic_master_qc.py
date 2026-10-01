#!/usr/bin/env python3
"""BRAIN Cinematic Master QC.

Separates technical media validity from cinematic/content validity.
The gate is intentionally conservative: missing evidence is a failure, not
an assumption of quality.

Inputs:
  --video  final.mp4
  --manifest manifest.json

Outputs:
  cinematic_master_qc.json
  exit 0 only when every required gate passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def ffprobe(video: Path) -> dict[str, Any]:
    p = run([
        "ffprobe", "-v", "error",
        "-show_entries",
        "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,bit_rate,sample_rate,channels,duration",
        "-of", "json", str(video),
    ], 120)
    if p.returncode != 0:
        raise RuntimeError("FFPROBE_FAILED:" + (p.stderr or "")[-1000:])
    return json.loads(p.stdout or "{}")


def sample_video(video: Path, duration: float, samples: int = 24) -> tuple[list[bytes], list[str]]:
    """Return compact grayscale frames and their hashes at evenly spaced times."""
    samples = max(8, min(samples, 48))
    # Raw gray frames are small enough for CI and avoid OpenCV/Pillow dependencies.
    width, height = 64, 36
    fps = samples / max(duration, 1.0)
    p = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(video),
        "-vf", f"fps={fps:.8f},scale={width}:{height},format=gray",
        "-frames:v", str(samples), "-f", "rawvideo", "-",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600, check=False)
    if p.returncode != 0:
        raise RuntimeError("FRAME_SAMPLE_FAILED:" + (p.stderr.decode(errors="replace"))[-1000:])
    frame_size = width * height
    raw = p.stdout
    frames = [raw[i:i + frame_size] for i in range(0, len(raw), frame_size) if len(raw[i:i + frame_size]) == frame_size]
    hashes = [hashlib.sha256(x).hexdigest() for x in frames]
    return frames, hashes


def frame_diff(a: bytes, b: bytes) -> float:
    if not a or len(a) != len(b):
        return 0.0
    return sum(abs(x - y) for x, y in zip(a, b)) / (255.0 * len(a))


def audio_metrics(video: Path, duration: float) -> dict[str, Any]:
    """Estimate whether audio is more than a repeated near-pure tone.

    This is evidence, not speech/music semantic recognition. The manifest must
    still declare voice/music/SFX assets for those content classes.
    """
    seconds = min(max(duration, 1.0), 180.0)
    p = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(video),
        "-t", f"{seconds:.3f}", "-ac", "1", "-ar", "8000",
        "-f", "s16le", "-",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, check=False)
    if p.returncode != 0:
        return {"status": "FAILED", "reason": "AUDIO_DECODE_FAILED"}
    import struct
    raw = p.stdout
    if len(raw) < 16000:
        return {"status": "FAILED", "reason": "AUDIO_TOO_SHORT"}
    vals = struct.unpack("<" + "h" * (len(raw) // 2), raw[:len(raw) // 2 * 2])
    # Use non-overlapping 1-second windows.
    win = 8000
    entropies = []
    dominant_ratios = []
    rms = []
    for i in range(0, len(vals) - win + 1, win):
        x = vals[i:i + win]
        power = [float(v) * float(v) for v in x]
        rms.append(math.sqrt(sum(power) / len(power)) / 32768.0)
        # Downsample into frequency bands using a tiny DFT over 64 bins.
        bands = [0.0] * 64
        for n in range(0, len(x), 16):
            v = x[n] / 32768.0
            for k in range(64):
                bands[k] += abs(v * math.cos(2 * math.pi * k * n / 128.0))
        total = sum(bands) or 1.0
        probs = [b / total for b in bands]
        entropy = -sum(q * math.log(q + 1e-12) for q in probs) / math.log(len(probs))
        entropies.append(entropy)
        dominant_ratios.append(max(probs))
    return {
        "status": "VERIFIED",
        "mean_rms": round(sum(rms) / max(len(rms), 1), 5),
        "mean_spectral_entropy": round(sum(entropies) / max(len(entropies), 1), 4),
        "mean_dominant_band_ratio": round(sum(dominant_ratios) / max(len(dominant_ratios), 1), 4),
        "tone_like": (sum(entropies) / max(len(entropies), 1)) < 0.22 and (sum(dominant_ratios) / max(len(dominant_ratios), 1)) > 0.55,
    }


def scene_signatures(manifest: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    parts = manifest.get("parts_manifest") or manifest.get("shots") or []
    sigs: list[str] = []
    normalized: list[dict[str, Any]] = []
    for item in parts:
        scene = item.get("scene") or {}
        # Prefer explicit scene_id; otherwise hash stable scene structure.
        explicit = item.get("scene_id") or scene.get("scene_id")
        if explicit:
            sig = str(explicit)
        else:
            stable = {
                "title": item.get("title"),
                "scene": scene,
                "character_ids": item.get("character_ids") or scene.get("character_ids"),
                "world_id": item.get("world_id") or scene.get("world_id"),
            }
            sig = hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
        sigs.append(sig)
        normalized.append(item)
    return sigs, normalized


def evaluate(video: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    probe = ffprobe(video)
    fmt = probe.get("format") or {}
    streams = probe.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(fmt.get("duration") or 0)
    size = int(fmt.get("size") or video.stat().st_size)
    video_bitrate = int(v.get("bit_rate") or 0) if v else 0
    if not video_bitrate and duration:
        video_bitrate = int((size * 8) / duration)

    frames, hashes = sample_video(video, duration)
    unique_hashes = len(set(hashes))
    adjacent_diffs = [frame_diff(frames[i], frames[i + 1]) for i in range(len(frames) - 1)]
    mean_motion = sum(adjacent_diffs) / max(len(adjacent_diffs), 1)
    transition_count = sum(1 for d in adjacent_diffs if d >= 0.12)
    frozen_count = sum(1 for d in adjacent_diffs if d < 0.01)
    duplicate_ratio = 1.0 - (unique_hashes / max(len(hashes), 1))

    black = run([
        "ffmpeg", "-v", "info", "-i", str(video), "-vf",
        "blackdetect=d=0.5:pix_th=0.98", "-an", "-f", "null", "-",
    ], 300)
    import re
    black_seconds = sum(float(m.group(1)) for m in re.finditer(r"black_duration:([0-9.]+)", black.stderr or ""))
    black_ratio = black_seconds / duration if duration else 1.0

    sigs, parts = scene_signatures(manifest)
    unique_scene_sigs = len(set(sigs))
    scene_count = len(parts)
    diversity_ratio = unique_scene_sigs / max(scene_count, 1)

    declared = manifest.get("cinematic_contract") or {}
    audio_decl = manifest.get("audio") or declared.get("audio") or {}
    required_classes = ["voice", "music", "sfx"]
    declared_audio_classes = {
        k: bool(audio_decl.get(k) or (isinstance(audio_decl.get(k + "_tracks"), list) and audio_decl.get(k + "_tracks")))
        for k in required_classes
    }

    character_bible = manifest.get("character_bible") or declared.get("character_bible") or {}
    world_bible = manifest.get("world_bible") or declared.get("world_bible") or {}
    continuity_declared = bool(character_bible or world_bible or declared.get("continuity"))

    text_policy = declared.get("text_overlay_policy", "deny")
    text_evidence = bool(manifest.get("text_overlay_qc") or declared.get("text_overlay_qc"))
    if text_policy == "deny":
        text_check = text_evidence
    else:
        text_check = True

    checks = {
        "scene_count": scene_count >= int(os.getenv("BRAIN_CINEMATIC_MIN_SCENES", "24")),
        "visual_diversity": diversity_ratio >= float(os.getenv("BRAIN_CINEMATIC_MIN_DIVERSITY", "0.50")),
        "image_presence": len(frames) >= 8 and unique_hashes >= 4,
        "motion": mean_motion >= float(os.getenv("BRAIN_CINEMATIC_MIN_MOTION", "0.015")),
        "scene_transitions": transition_count >= int(os.getenv("BRAIN_CINEMATIC_MIN_TRANSITIONS", "8")),
        "character_story_continuity": continuity_declared,
        "audio_stream": a is not None,
        "voice_evidence": declared_audio_classes["voice"],
        "music_evidence": declared_audio_classes["music"],
        "sfx_evidence": declared_audio_classes["sfx"],
        "audio_diversity": not audio_metrics(video, duration).get("tone_like", False),
        "black_frames": black_ratio <= float(os.getenv("BRAIN_CINEMATIC_MAX_BLACK_RATIO", "0.01")),
        "frozen_frames": (frozen_count / max(len(adjacent_diffs), 1)) <= float(os.getenv("BRAIN_CINEMATIC_MAX_FROZEN_RATIO", "0.15")),
        "duplicate_scene_detection": duplicate_ratio <= float(os.getenv("BRAIN_CINEMATIC_MAX_DUPLICATE_RATIO", "0.50")),
        "text_overlay_check": text_check,
        "bitrate_sanity": video_bitrate >= int(os.getenv("BRAIN_CINEMATIC_MIN_VIDEO_BITRATE", "800000")),
        "manifest_video_consistency": scene_count == int(manifest.get("parts", scene_count)) if manifest.get("parts") is not None else scene_count > 0,
    }
    # The content gate is separate from ffprobe/master technical validity.
    technical = {
        "duration_s": duration,
        "video_stream": v is not None,
        "audio_stream": a is not None,
        "width": (v or {}).get("width"),
        "height": (v or {}).get("height"),
        "size_bytes": size,
        "video_bitrate_bps": video_bitrate,
    }
    passed = all(checks.values())
    return {
        "status": "CINEMATIC_QC_PASSED" if passed else "CINEMATIC_QC_FAILED",
        "gate": "CINEMATIC_MASTER_QC",
        "checks": checks,
        "technical_snapshot": technical,
        "scene_analysis": {
            "scene_count": scene_count,
            "unique_scene_signatures": unique_scene_sigs,
            "visual_diversity_ratio": round(diversity_ratio, 4),
            "duplicate_ratio": round(duplicate_ratio, 4),
            "sample_count": len(frames),
            "transition_count": transition_count,
            "mean_motion": round(mean_motion, 5),
            "frozen_ratio": round(frozen_count / max(len(adjacent_diffs), 1), 4),
        },
        "black_ratio": round(black_ratio, 5),
        "audio_analysis": audio_metrics(video, duration),
        "declared_audio_classes": declared_audio_classes,
        "text_overlay_policy": text_policy,
        "continuity_evidence_present": continuity_declared,
        "failure_reasons": [k for k, ok in checks.items() if not ok],
    }


REPAIR_MAP = {
    "scene_count": "INCREASE_DISTINCT_SCENE_COUNT",
    "visual_diversity": "GENERATE_MATERIALLY_DIVERSE_VISUALS",
    "image_presence": "REQUIRE_REAL_IMAGE_OR_DRAWING_ASSETS",
    "motion": "REQUIRE_CAMERA_OR_ELEMENT_MOTION",
    "scene_transitions": "REQUIRE_REAL_SCENE_TRANSITIONS",
    "character_story_continuity": "REQUIRE_SCENE_CHARACTER_WORLD_BIBLES",
    "voice_evidence": "REQUIRE_VOICE_NARRATION_ASSETS",
    "music_evidence": "REQUIRE_MUSIC_ASSETS",
    "sfx_evidence": "REQUIRE_SFX_AMBIENCE_ASSETS",
    "audio_diversity": "REBUILD_REPEATED_TONE_AUDIO",
    "black_frames": "REPLACE_BLACK_SEGMENTS",
    "frozen_frames": "REBUILD_FROZEN_SEGMENTS",
    "duplicate_scene_detection": "REBUILD_DUPLICATE_SCENES",
    "text_overlay_check": "REMOVE_UNINTENDED_TEXT_OVERLAYS",
    "bitrate_sanity": "INCREASE_VIDEO_ENCODING_QUALITY",
    "manifest_video_consistency": "REPAIR_MANIFEST_RENDER_ALIGNMENT",
}

def build_repair_manifest(qc: dict[str, Any]) -> dict[str, Any]:
    failures = qc.get("failure_reasons", [])
    requirements = [REPAIR_MAP.get(x, "MANUAL_REVIEW:" + x) for x in failures]
    return {
        "status": "REPAIR_REQUIRED" if failures else "NO_REPAIR_REQUIRED",
        "source_gate": "CINEMATIC_MASTER_QC",
        "failure_reasons": failures,
        "mandatory_requirements": requirements,
        "blocking": bool(failures),
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output", default="cinematic_master_qc.json")
    args = ap.parse_args()
    result = evaluate(Path(args.video), Path(args.manifest))
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    repair = build_repair_manifest(result)
    repair_path = Path(args.output).with_name("cinematic_repair_manifest.json")
    repair_path.write_text(json.dumps(repair, ensure_ascii=False, indent=2), encoding="utf-8")
    result["repair_manifest"] = repair
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "CINEMATIC_QC_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
