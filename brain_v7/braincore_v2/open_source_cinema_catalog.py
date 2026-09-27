"""Curated open-source cinema integration catalog.

The catalog records integration targets, not copied source code. Each project
must be reviewed for its current license/model-weight terms before commercial
deployment.
"""
from __future__ import annotations

from typing import Any

CATALOG: list[dict[str, Any]] = [
    {
        "name": "ComfyUI Cinema Pipeline",
        "repo": "https://github.com/ismael-joffroy-chandoutis/comfyui-cinema-pipeline",
        "use": ["cinema workflows", "Blender geometry", "ControlNet", "Wan", "LTX", "mobile/remote orchestration"],
        "factory_role": "reference/workflow library",
    },
    {
        "name": "ComfyUI-Cine-con-IA",
        "repo": "https://github.com/chaLords/ComfyUI-Cine-con-IA",
        "use": ["cinematic shot controls", "camera planning", "Wan 2.2", "LTX", "Hunyuan"],
        "factory_role": "ComfyUI node/workflow source",
    },
    {
        "name": "ComfyUI Wan Video Pipeline",
        "repo": "https://github.com/lilinsong1/comfyui-wan-video-pipeline",
        "use": ["audio-first", "T2V/I2V", "last-frame continuity", "upscale"],
        "factory_role": "shot execution pattern",
        "license_note": "Repository states MIT; verify current upstream terms before redistribution.",
    },
    {
        "name": "KupkaProd Cinema Pipeline",
        "repo": "https://github.com/Matticusnicholas/KupkaProd-Cinema-Pipeline",
        "use": ["screenplay breakdown", "storyboard", "multi-take selection", "LTX", "FFmpeg"],
        "factory_role": "director/production workflow reference",
    },
    {
        "name": "ComfyUI-MovieGenerator",
        "repo": "https://github.com/UbivisMedia/ComfyUI-MovieGenerator",
        "use": ["structured screenplay", "character casting", "I2V", "match cuts", "assembly"],
        "factory_role": "end-to-end architecture reference",
    },
    {
        "name": "4brospix",
        "repo": "https://github.com/koo-bros/4brospix",
        "use": ["manifest-driven production", "Codex-controlled ComfyUI", "Blender layout", "post-production"],
        "factory_role": "agent/manifest architecture reference",
    },
]


def catalog() -> list[dict[str, Any]]:
    return [dict(item) for item in CATALOG]


def integration_plan() -> dict[str, Any]:
    return {
        "policy": "adapter-first; do not vendor external source code into the factory",
        "priority": [
            "ComfyUI workflow execution",
            "Wan/LTX/Hunyuan model routing",
            "audio-first timing",
            "last-frame/first-frame continuity",
            "storyboard/keyframe selection",
            "OTIO timeline handoff",
            "FFmpeg master",
        ],
        "license_gate": "review code, model, weights and commercial terms independently before shipping",
    }
