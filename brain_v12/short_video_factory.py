"""BRAIN Short Video Factory.

Provider-neutral orchestration for short videos. The factory does not vendor
third-party model code; it uses clean adapter contracts and records provenance.

Design:
  script/image/audio -> duration/timing plan -> lip-sync backend -> FFmpeg/QC

External backends are opt-in through environment variables. The free local
path remains usable without paid APIs.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OSSComponent:
    name: str
    origin: str
    role: str
    license: str
    runtime: str
    source: str


OSS_COMPONENTS = (
    OSSComponent("MuseTalk", "China", "audio-driven lip synchronization", "MIT", "optional", "https://github.com/TMElyralab/MuseTalk"),
    OSSComponent("SadTalker", "China", "single-image talking-head animation", "Apache-2.0", "optional", "https://github.com/OpenTalker/SadTalker"),
    OSSComponent("LivePortrait", "China", "portrait animation/retargeting", "MIT", "optional", "https://github.com/KlingAIResearch/LivePortrait"),
    OSSComponent("VOICEVOX Core", "Japan", "local TTS core", "MIT", "optional", "https://github.com/VOICEVOX/voicevox_core"),
    OSSComponent("BlueMagpie-TTS", "Taiwan", "Taiwan Mandarin/code-switching TTS", "Apache-2.0", "optional", "https://github.com/OpenFormosa/BlueMagpie-TTS"),
    OSSComponent("RHVoice", "Russia", "local Russian/multilingual TTS", "GPL-2.0/LGPL-2.1 core", "optional", "https://github.com/RHVoice/RHVoice"),
    OSSComponent("NileTTS", "Morocco research", "Arabic TTS training/inference research", "Apache-2.0", "research", "https://github.com/KickItLikeShika/NileTTS"),
)


@dataclass
class ShortVideoPlan:
    text: str
    image: str
    audio: str | None
    duration: float
    fps: int
    width: int
    height: int
    lipsync_backend: str
    tts_backend: str
    word_timing: list[dict[str, Any]]
    provenance: list[dict[str, Any]]


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def estimate_duration(text: str, wpm: float = 145.0) -> float:
    """Conservative speech duration estimate for planning only."""
    words = max(1, len(_clean_text(text).split()))
    return max(1.5, min(60.0, words / max(80.0, wpm) * 60.0 + 0.35))


def word_timing(text: str, duration: float) -> list[dict[str, Any]]:
    words = _clean_text(text).split()
    if not words:
        return []
    weights = [max(1, len(re.sub(r"[^\w\u0600-\u06ff]", "", w))) for w in words]
    total = float(sum(weights))
    cursor = 0.0
    out = []
    for idx, (word, weight) in enumerate(zip(words, weights)):
        span = duration * weight / total
        out.append({
            "index": idx,
            "word": word,
            "start": round(cursor, 3),
            "end": round(cursor + span, 3),
            "mouth": "closed" if re.search(r"[.!?؟،,؛;]$", word) else "open",
        })
        cursor += span
    if out:
        out[-1]["end"] = round(duration, 3)
    return out


def configured_backend(kind: str, preferred: str = "auto") -> str:
    preferred = (preferred or "auto").strip().lower()
    if preferred != "auto":
        return preferred
    if kind == "lipsync":
        if os.getenv("BRAIN_MUSETALK_CMD"):
            return "musetalk"
        if os.getenv("BRAIN_SADTALKER_CMD"):
            return "sadtalker"
        return "local-timing"
    if kind == "tts":
        if os.getenv("BRAIN_VOICEVOX_URL"):
            return "voicevox"
        if os.getenv("BRAIN_RHVOICE_CMD"):
            return "rhvoice"
        if os.getenv("BRAIN_BLUEMAGPIE_CMD"):
            return "bluemagpie"
        return "none"
    raise ValueError("UNKNOWN_BACKEND_KIND")


def backend_status() -> dict[str, Any]:
    commands = {
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "musetalk": os.getenv("BRAIN_MUSETALK_CMD"),
        "sadtalker": os.getenv("BRAIN_SADTALKER_CMD"),
        "rhvoice": os.getenv("BRAIN_RHVOICE_CMD"),
        "bluemagpie": os.getenv("BRAIN_BLUEMAGPIE_CMD"),
        "voicevox_url": os.getenv("BRAIN_VOICEVOX_URL"),
    }
    return {
        "ok": bool(commands["ffmpeg"] and commands["ffprobe"]),
        "free_local_ready": bool(commands["ffmpeg"] and commands["ffprobe"]),
        "commands": commands,
        "lipsync": configured_backend("lipsync"),
        "tts": configured_backend("tts"),
    }


def build_plan(
    text: str,
    image: str,
    audio: str | None = None,
    duration: float | None = None,
    aspect: str = "9:16",
    lipsync: str = "auto",
    tts: str = "auto",
) -> dict[str, Any]:
    text = _clean_text(text)
    if not text:
        raise ValueError("SHORT_VIDEO_TEXT_REQUIRED")
    if not image:
        raise ValueError("SHORT_VIDEO_IMAGE_REQUIRED")
    duration = float(duration or estimate_duration(text))
    if duration < 1.0 or duration > 60.0:
        raise ValueError("SHORT_VIDEO_DURATION_OUT_OF_RANGE")
    if aspect == "16:9":
        width, height = 1920, 1080
    elif aspect == "1:1":
        width, height = 1080, 1080
    else:
        width, height = 1080, 1920
    lp = configured_backend("lipsync", lipsync)
    tp = configured_backend("tts", tts)
    provenance = [asdict(x) for x in OSS_COMPONENTS if (
        (lp == "musetalk" and x.name == "MuseTalk") or
        (lp == "sadtalker" and x.name == "SadTalker") or
        (lp == "liveportrait" and x.name == "LivePortrait") or
        (tp == "voicevox" and x.name == "VOICEVOX Core") or
        (tp == "bluemagpie" and x.name == "BlueMagpie-TTS") or
        (tp == "rhvoice" and x.name == "RHVoice") or
        (tp == "niletts" and x.name == "NileTTS")
    )]
    return asdict(ShortVideoPlan(
        text=text,
        image=image,
        audio=audio,
        duration=duration,
        fps=30,
        width=width,
        height=height,
        lipsync_backend=lp,
        tts_backend=tp,
        word_timing=word_timing(text, duration),
        provenance=provenance,
    ))


def command_for_lipsync(plan: dict[str, Any], output: str) -> list[str]:
    """Build an executable command only when a configured OSS adapter exists."""
    backend = plan["lipsync_backend"]
    image, audio = plan["image"], plan.get("audio")
    if not audio:
        raise ValueError("SHORT_VIDEO_AUDIO_REQUIRED_FOR_LIPSYNC")
    if backend == "musetalk":
        template = os.getenv("BRAIN_MUSETALK_CMD", "").strip()
        if not template:
            raise ValueError("MUSETALK_NOT_CONFIGURED")
    elif backend == "sadtalker":
        template = os.getenv("BRAIN_SADTALKER_CMD", "").strip()
        if not template:
            raise ValueError("SADTALKER_NOT_CONFIGURED")
    else:
        raise ValueError("NO_MODEL_LIPSYNC_BACKEND_CONFIGURED")
    values = {
        "image": shlex.quote(str(image)),
        "audio": shlex.quote(str(audio)),
        "output": shlex.quote(str(output)),
    }
    return [part.format(**values) for part in shlex.split(template)]


def registry() -> list[dict[str, Any]]:
    return [asdict(x) for x in OSS_COMPONENTS]
