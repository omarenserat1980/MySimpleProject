"""Real ComfyUI video execution adapter.

This adapter never installs models or silently falls back to Pillow/FFmpeg.
It submits a prepared ComfyUI workflow, polls its history, downloads the
first produced video file, and validates that a non-empty video artifact exists.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .open_source_adapters import ComfyUIAdapter


class VideoGenerationError(RuntimeError):
    pass


class ComfyUIVideoAdapter:
    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.api = ComfyUIAdapter(self.base_url, timeout=timeout)

    def probe(self) -> dict:
        try:
            stats = self.api.system_stats()
            return {"available": True, "system_stats": stats}
        except Exception as exc:
            return {"available": False, "error": str(exc)}

    def submit(self, workflow: dict, client_id: str = "brain-film") -> str:
        if not isinstance(workflow, dict) or not workflow:
            raise VideoGenerationError("workflow must be a non-empty ComfyUI prompt graph")
        result = self.api.queue_prompt(workflow, client_id=client_id)
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            raise VideoGenerationError("ComfyUI did not return prompt_id: " + json.dumps(result)[:2000])
        return str(prompt_id)

    def wait_for_video(
        self,
        prompt_id: str,
        output_dir: str | Path,
        timeout_seconds: int = 900,
        poll_seconds: float = 2.0,
    ) -> Path:
        deadline = time.monotonic() + max(1, timeout_seconds)
        while time.monotonic() < deadline:
            history = self.api.request("GET", f"/history/{prompt_id}")
            item = history.get(prompt_id) if isinstance(history, dict) else None
            if item:
                status = item.get("status", {})
                if status.get("status_str") == "error" or status.get("completed") is False:
                    messages = status.get("messages", [])
                    raise VideoGenerationError(
                        "ComfyUI workflow failed: " + json.dumps(messages)[:4000]
                    )
                video = self._find_video(item.get("outputs", {}))
                if video:
                    return self._download(video, Path(output_dir))
            time.sleep(max(0.2, poll_seconds))
        raise VideoGenerationError(f"timed out waiting for ComfyUI prompt {prompt_id}")

    @staticmethod
    def _find_video(outputs: dict) -> dict | None:
        for node_output in outputs.values():
            for key in ("gifs", "videos"):
                for item in node_output.get(key, []) or []:
                    filename = str(item.get("filename", ""))
                    if Path(filename).suffix.lower() in {".mp4", ".webm", ".mov", ".mkv"}:
                        return item
        return None

    def _download(self, item: dict, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(str(item["filename"])).name
        query = urlencode({
            "filename": filename,
            "subfolder": str(item.get("subfolder", "")),
            "type": str(item.get("type", "output")),
        })
        req = Request(self.base_url + "/view?" + query, headers={"User-Agent": "Brain-ComfyUI-Video/1.0"})
        target = output_dir / filename
        with urlopen(req, timeout=30) as response, target.open("wb") as fh:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        if not target.exists() or target.stat().st_size <= 1024:
            target.unlink(missing_ok=True)
            raise VideoGenerationError("ComfyUI returned an empty/too-small video artifact")
        return target

    def generate(
        self,
        workflow: dict,
        output_dir: str | Path,
        *,
        client_id: str = "brain-film",
        timeout_seconds: int = 900,
        poll_seconds: float = 2.0,
    ) -> dict:
        probe = self.probe()
        if not probe["available"]:
            raise VideoGenerationError("ComfyUI unavailable: " + probe.get("error", "unknown"))
        prompt_id = self.submit(workflow, client_id=client_id)
        artifact = self.wait_for_video(
            prompt_id, output_dir, timeout_seconds=timeout_seconds, poll_seconds=poll_seconds
        )
        return {
            "backend": "comfyui",
            "prompt_id": prompt_id,
            "artifact": str(artifact),
            "size_bytes": artifact.stat().st_size,
            "verified_nonempty": True,
        }
