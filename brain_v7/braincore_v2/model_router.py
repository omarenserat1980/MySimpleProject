"""Model-agnostic cinema router for Electronic Brain V6.

The router keeps the factory's director/QC/memory layers independent from any
single generation backend. It can target a ComfyUI server or fall back to the
existing BrainMediaProvider. Wan/LTX/Hunyuan are selected through a workflow
profile rather than hard-coded into the director.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Protocol
import httpx


class MediaBackend(Protocol):
    def render(self, *, shot: dict[str, Any], authorized: bool = False) -> dict[str, Any]: ...


PROFILES: dict[str, dict[str, Any]] = {
    "wan": {"family": "wan", "mode": "i2v", "priority": 100},
    "ltx": {"family": "ltx", "mode": "i2v", "priority": 90},
    "hunyuan": {"family": "hunyuan", "mode": "i2v", "priority": 80},
    "comfyui": {"family": "comfyui", "mode": "workflow", "priority": 70},
    "fallback": {"family": "existing_provider", "mode": "provider", "priority": 10},
}


class ComfyUIBackend:
    def __init__(self) -> None:
        self.base_url = os.getenv("COMFYUI_URL", "").rstrip("/")
        self.client_id = os.getenv("COMFYUI_CLIENT_ID", "electronic-brain")
        self.workflow_json = os.getenv("COMFYUI_WORKFLOW_JSON", "")
        self.timeout = float(os.getenv("COMFYUI_TIMEOUT_SECONDS", "900"))
        self.poll = float(os.getenv("COMFYUI_POLL_SECONDS", "3"))
        self.max_polls = max(1, int(os.getenv("COMFYUI_MAX_POLLS", "300")))

    def configured(self) -> bool:
        return bool(self.base_url and self.workflow_json)

    def _workflow(self, shot: dict[str, Any]) -> dict[str, Any]:
        workflow = json.loads(self.workflow_json)
        replacements = {
            "PROMPT": shot.get("visual_prompt", ""),
            "NEGATIVE_PROMPT": shot.get("negative_prompt", ""),
            "IMAGE_REFERENCE_PROMPT": shot.get("image_reference_prompt", ""),
            "SOUND_DESIGN_PROMPT": shot.get("sound_design_prompt", ""),
            "VOICE_PROMPT": shot.get("voice_prompt", ""),
            "SHOT_ID": shot.get("shot_id", ""),
            "DURATION": shot.get("duration_s", 5),\n            "INFERENCE_PROFILE": (shot.get("generation") or {}).get("inference_profile", "production"),\n            "SAMPLING_STEPS": (shot.get("generation") or {}).get("sampling_steps", 20),\n            "QUANTIZATION": (shot.get("generation") or {}).get("quantization", "bf16"),\n            "ATTENTION": (shot.get("generation") or {}).get("attention", "default"),
        }
        encoded = json.dumps(workflow, ensure_ascii=False)
        for key, value in replacements.items():
            encoded = encoded.replace("{{" + key + "}}", str(value))
        return json.loads(encoded)

    def render(self, *, shot: dict[str, Any], authorized: bool = False) -> dict[str, Any]:
        if not authorized:
            return {"status": "AUTHORIZATION_REQUIRED"}
        if not self.configured():
            return {"status": "COMFYUI_NOT_CONFIGURED"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                payload = {"prompt": self._workflow(shot), "client_id": self.client_id}
                queued = client.post(self.base_url + "/prompt", json=payload)
                queued.raise_for_status()
                data = queued.json()
                prompt_id = data.get("prompt_id")
                if not prompt_id:
                    return {"status": "COMFYUI_SUBMISSION_UNVERIFIED", "provider_result": data}
                for _ in range(self.max_polls):
                    time.sleep(self.poll)
                    history = client.get(self.base_url + "/history/" + str(prompt_id))
                    history.raise_for_status()
                    item = history.json().get(str(prompt_id))
                    if not item:
                        continue
                    outputs = item.get("outputs", {})
                    media = self._find_media(outputs)
                    if media:
                        return {
                            "status": "VERIFIED_COMPLETED",
                            "video_ref": media,
                            "provider": "comfyui",
                            "model_family": shot.get("model_family"),
                            "prompt_id": prompt_id,
                            "provider_result": item,
                            "shot_id": shot.get("shot_id"),
                        }
                    if item.get("status", {}).get("status_str") == "error":
                        return {"status": "PROVIDER_FAILED", "provider_result": item, "prompt_id": prompt_id}
                return {"status": "PROVIDER_TIMEOUT", "prompt_id": prompt_id}
        except Exception as exc:
            return {"status": "PROVIDER_ERROR", "error": repr(exc), "provider": "comfyui"}

    @staticmethod
    def _find_media(outputs: dict[str, Any]) -> str | None:
        for node in outputs.values():
            for key in ("gifs", "videos", "images"):
                for item in node.get(key, []) if isinstance(node, dict) else []:
                    if isinstance(item, dict) and item.get("url"):
                        return item["url"]
        return None


class ModelRouter:
    """Select a backend without changing the film plan."""

    def __init__(self, fallback: MediaBackend) -> None:
        self.fallback = fallback
        self.comfy = ComfyUIBackend()
        self.requested = os.getenv("FACTORY_MODEL", "auto").strip().lower()

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": 1,
            "requested": self.requested,
            "comfyui_configured": self.comfy.configured(),
            "profiles": PROFILES,
            "routing": "auto -> configured backend -> existing provider fallback",
        }

    def _profile(self, shot: dict[str, Any]) -> str:
        requested = str(shot.get("model_family") or self.requested)
        if requested in PROFILES and requested != "auto":
            return requested
        for candidate in ("wan", "ltx", "hunyuan", "comfyui"):
            if self.comfy.configured():
                return candidate
        return "fallback"

    def render(self, *, shot: dict[str, Any], authorized: bool = False) -> dict[str, Any]:
        family = self._profile(shot)
        enriched = dict(shot)
        enriched["model_family"] = family
        enriched["router_snapshot"] = self.snapshot()
        if self.comfy.configured():
            result = self.comfy.render(shot=enriched, authorized=authorized)
            if result.get("status") == "VERIFIED_COMPLETED":
                result["router"] = {"selected": family, "fallback_used": False}
                return result
        result = self.fallback.render(shot=enriched, authorized=authorized)
        result["router"] = {"selected": family, "fallback_used": True}
        return result
