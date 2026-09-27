"""Provider-neutral audio router for cinematic dialogue and music.

The factory can send structured audio intents to an external/local service
without coupling story logic to a specific TTS or music implementation.
"""
from __future__ import annotations

import os
from typing import Any
import httpx


class AudioRouter:
    def __init__(self) -> None:
        self.url = os.getenv("AUDIO_PROVIDER_URL", "").strip()
        self.key = os.getenv("AUDIO_PROVIDER_API_KEY", "").strip()
        self.timeout = float(os.getenv("AUDIO_PROVIDER_TIMEOUT_SECONDS", "600"))

    def configured(self) -> bool:
        return bool(self.url)

    def snapshot(self) -> dict[str, Any]:
        return {
            "configured": self.configured(),
            "voice_model": os.getenv("AUDIO_VOICE_MODEL", "auto"),
            "music_model": os.getenv("AUDIO_MUSIC_MODEL", "auto"),
            "supported_intents": ["dialogue", "voice_clone", "ambience", "foley", "music", "mix"],
        }

    def render(self, *, shot: dict[str, Any], authorized: bool = False) -> dict[str, Any]:
        if not authorized:
            return {"status": "AUTHORIZATION_REQUIRED"}
        if not self.url:
            return {"status": "AUDIO_PROVIDER_NOT_CONFIGURED", "snapshot": self.snapshot()}
        payload = {
            "operation": "generate_audio",
            "shot_id": shot.get("shot_id"),
            "voice_prompt": shot.get("voice_prompt", ""),
            "sound_design_prompt": shot.get("sound_design_prompt", ""),
            "audio_prompt": shot.get("audio_prompt", ""),
            "duration_s": shot.get("duration_s"),
        }
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            ref = data.get("audio_ref") or data.get("output_url") or data.get("media_url")
            return {
                "status": "VERIFIED_COMPLETED" if ref else "SUBMISSION_UNVERIFIED",
                "audio_ref": ref,
                "provider_result": data,
                "shot_id": shot.get("shot_id"),
            }
        except Exception as exc:
            return {"status": "PROVIDER_ERROR", "error": repr(exc), "shot_id": shot.get("shot_id")}
