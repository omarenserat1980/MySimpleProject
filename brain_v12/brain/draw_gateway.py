"""Human-to-image routing for BRAIN.

Default is the free local Visual Engine. OpenAI image generation is optional
and requires an explicitly configured server-side API key.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any, Callable

from .. import visual_engine


_DRAW_WORDS = ("ارسم", "ارسم لي", "صورة", "draw", "image", "picture")
_CHATGPT_WORDS = ("chatgpt", "شات جي بي تي", "شاتجبت", "openai")


def parse_human_draw_request(message: str) -> dict[str, Any]:
    text = (message or "").strip()
    low = text.lower()
    is_draw = any(word in low for word in _DRAW_WORDS)
    wants_chatgpt = any(word in low for word in _CHATGPT_WORDS)
    prompt = re.sub(r"(?i)^.*?(?:ارسم(?:\s+لي)?|draw|create an image of|generate an image of)\s*", "", text).strip()
    if not prompt:
        prompt = text
    return {
        "ok": bool(is_draw),
        "intent": "DRAW_IMAGE" if is_draw else "CHAT",
        "provider": "openai" if wants_chatgpt else "local",
        "prompt": prompt or "منظر طبيعي",
    }


def draw_local(prompt: str, mode: str = "auto") -> dict[str, Any]:
    scene = visual_engine.compile_scene(prompt, mode)
    svg = visual_engine.render_svg(scene)
    valid = svg.startswith("<svg") and "</svg>" in svg and len(svg.encode("utf-8")) > 100
    return {
        "ok": valid,
        "provider": "local",
        "verified": valid,
        "scene": scene,
        "svg": svg,
        "format": "svg",
    }


def save_png_base64(data: str, target: Path) -> int:
    raw = base64.b64decode(data, validate=True)
    if len(raw) < 128:
        raise ValueError("IMAGE_TOO_SMALL")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return len(raw)


def draw_openai(prompt: str, generator: Callable[[str], dict[str, Any]], media_root: Path) -> dict[str, Any]:
    result = generator(prompt)
    if not result.get("ok"):
        return result
    data = result.get("b64_json") or result.get("image_base64")
    if not data:
        return {"ok": False, "error": "OPENAI_IMAGE_DATA_MISSING"}
    filename = "brain-openai-draw-" + __import__("uuid").uuid4().hex + ".png"
    target = media_root / filename
    size = save_png_base64(data, target)
    return {
        "ok": True,
        "provider": "openai",
        "verified": size >= 128,
        "filename": filename,
        "url": "/media/" + filename,
        "bytes": size,
        "format": "png",
        "model": result.get("model"),
    }
