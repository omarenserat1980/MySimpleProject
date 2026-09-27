"""Persistent V6 capability manifest for the factory."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .cinema_engine_v6 import CinemaEngineV6


def write_manifest(path: str | Path = "cinema_engine_v6_manifest.json") -> dict[str, Any]:
    manifest = {
        "engine": CinemaEngineV6().snapshot(),
        "environment": {
            "factory_model": os.getenv("FACTORY_MODEL", "auto"),
            "comfyui_url_configured": bool(os.getenv("COMFYUI_URL")),
            "factory_render_concurrency": os.getenv("FACTORY_RENDER_CONCURRENCY", "3"),
        },
        "updated_at": time.time(),
    }
    target = Path(path)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
