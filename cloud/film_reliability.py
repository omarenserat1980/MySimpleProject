"""Reliable cinematic rendering supervisor.

The engine never reports success merely because a renderer exits zero.
A film becomes successful only after an independent ffprobe/QC gate passes.
Failed attempts are isolated, retried, and never promoted to the final master.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from cloud.cinematic_sensory_qc import CinematicSensoryQC

ROOT = Path(__file__).resolve().parents[1]


class FilmReliabilityError(RuntimeError):
    pass


def _int_env(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(low, min(high, value))


class FilmReliabilityEngine:
    def __init__(self, output_dir: Path, max_attempts: int | None = None) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.attempts = max_attempts or _int_env("CINEMATIC_MAX_ATTEMPTS", 3, 1, 5)
        self.timeout = _int_env("BRAIN_FACTORY_TIMEOUT_SECONDS", 3600, 60, 7200)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir = self.output_dir / ".attempts"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.final = self.output_dir / "final.mp4"
        self.manifest = self.output_dir / "film_manifest.json"
        self.log = self.output_dir / "reliability.log"

    def _log(self, message: str) -> None:
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {message}\n")

    def _prepare_env(self, payload: dict[str, Any], attempt_dir: Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(ROOT),
            "FACTORY_ONE_SHOT": "1",
            "FACTORY_ALLOW_PRODUCTION": "1",
            "FACTORY_REQUIRE_REAL_MEDIA": "1",
            "FACTORY_ALLOW_LOCAL_FALLBACK": os.getenv("FACTORY_ALLOW_LOCAL_FALLBACK", "1"),
            "FACTORY_MEDIA_ROUTE": os.getenv("FACTORY_MEDIA_ROUTE", "local_ffmpeg_cinematic"),
            "FACTORY_DURATION_SECONDS": str(max(1, min(1800, int(payload.get("target_minutes", 12)) * 60))),
            "FACTORY_OUTPUT_DIR": str(attempt_dir),
            "LOCAL_MEDIA_DIR": str(attempt_dir),
            "BRAIN_STATE_DIR": os.getenv("BRAIN_STATE_DIR", str(ROOT / ".brain_state")),
            "FACTORY_STATE_PATH": str(attempt_dir / "factory_state.json"),
            "FACTORY_PROJECT_MANIFEST": str(attempt_dir / "cinematic_project_manifest.json"),
            "CINEMA_ENGINE_MANIFEST": str(attempt_dir / "cinema_engine_v6_manifest.json"),
            "FACTORY_TOPICS_JSON": json.dumps([payload], ensure_ascii=False),
            "FACTORY_OBJECTIVE": "Produce and verify the requested cinematic film: " + str(payload.get("title", "")),
        })
        return env

    def _qc(self, video: Path) -> dict[str, Any]:
        if not video.is_file() or video.stat().st_size < 1024:
            return {"ok": False, "error": "missing_or_tiny_mp4"}
        try:
            from brain_v12 import brain_ffmpeg
            ffprobe = brain_ffmpeg.ffprobe()
        except Exception as exc:
            return {"ok": False, "error": "ffprobe_unavailable", "details": str(exc)}
        probe = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "format=duration,size,format_name",
             "-show_entries", "stream=codec_type,codec_name,width,height",
             "-of", "json", str(video)],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if probe.returncode != 0:
            return {"ok": False, "error": "ffprobe_failed", "details": probe.stderr[-2000:]}
        try:
            data = json.loads(probe.stdout)
            fmt = data["format"]
            streams = data.get("streams", [])
            duration = float(fmt.get("duration", 0))
            size = int(fmt.get("size", 0))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return {"ok": False, "error": "invalid_probe", "details": str(exc)}
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        if duration <= 0 or size < 1024 or not has_video or not has_audio:
            return {"ok": False, "error": "media_qc_failed", "probe": data}
        return {"ok": True, "duration": duration, "size": size, "format": fmt,
                "streams": streams}

    def _sensory_qc(self, payload: dict[str, Any]) -> dict[str, Any]:
        qc = CinematicSensoryQC()
        shots = payload.get("shots") or []
        if not shots:
            return {"ok": True, "mode": "manifest_not_available", "requires_review": False}
        issues = []
        previous = None
        for index, shot in enumerate(shots):
            shot_id = str(shot.get("id") or shot.get("shot_id") or f"shot-{index + 1}")
            qc.inspect_shot(
                shot_id,
                visual=str(shot.get("visual") or shot.get("description") or ""),
                audio=str(shot.get("audio") or shot.get("voice") or shot.get("sfx") or ""),
            )
            current = {
                "character": shot.get("character"),
                "location": shot.get("location"),
                "time": shot.get("time"),
                "audio_signature": shot.get("audio_signature") or shot.get("sfx"),
            }
            if previous is not None:
                issues.extend(qc.continuity_check(previous, current)["issues"])
            previous = current
        return {
            "ok": not issues,
            "inspected_shots": len(shots),
            "issues": sorted(set(issues)),
            "requires_review": bool(issues),
            "audit": qc.audit(),
        }

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.final.unlink(missing_ok=True)
        self.manifest.unlink(missing_ok=True)
        history: list[dict[str, Any]] = []

        for attempt in range(1, self.attempts + 1):
            attempt_dir = self.work_dir / f"attempt-{attempt}"
            if attempt_dir.exists():
                shutil.rmtree(attempt_dir)
            attempt_dir.mkdir(parents=True, exist_ok=True)
            self._log(f"ATTEMPT {attempt}/{self.attempts}: start")

            env = self._prepare_env(payload, attempt_dir)
            log_path = attempt_dir / "factory.log"
            started = time.time()
            try:
                with log_path.open("w", encoding="utf-8") as fh:
                    proc = subprocess.run(
                        [sys.executable, "-m", "brain_v7.braincore_v2.background_factory_worker"],
                        cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT,
                        timeout=self.timeout, check=False,
                    )
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                rc = 124
                self._log(f"ATTEMPT {attempt}: renderer timeout")
            candidate = attempt_dir / "final.mp4"
            qc = self._qc(candidate)
            sensory_qc = self._sensory_qc(payload)
            record = {"attempt": attempt, "return_code": rc, "qc": qc, "sensory_qc": sensory_qc,
                      "elapsed_seconds": round(time.time() - started, 2)}
            history.append(record)
            self._log(f"ATTEMPT {attempt}: rc={rc} media_qc={qc.get('ok')} sensory_qc={sensory_qc.get('ok')}")

            if rc == 0 and qc.get("ok") and sensory_qc.get("ok"):
                staging = self.output_dir / ".final.mp4.tmp"
                shutil.copyfile(candidate, staging)
                final_qc = self._qc(staging)
                if not final_qc.get("ok"):
                    staging.unlink(missing_ok=True)
                    history[-1]["promotion_qc"] = final_qc
                    continue
                os.replace(staging, self.final)
                manifest = {
                    "status": "VERIFIED_COMPLETED",
                    "profile": "BRAIN CLOUD FILM RELIABILITY ENGINE",
                    "runtime": "brain_cloud",
                    "device_required": False,
                    "termux_required": False,
                    "attempt": attempt,
                    "max_attempts": self.attempts,
                    "video": str(self.final),
                    "bytes": self.final.stat().st_size,
                    "verification": {"media": final_qc, "sensory": sensory_qc},
                    "attempt_history": history,
                }
                self.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                self._log(f"SUCCESS: verified master promoted on attempt {attempt}")
                return {"ok": True, "video_path": str(self.final),
                        "manifest_path": str(self.manifest), "verification": {"media": final_qc, "sensory": sensory_qc},
                        "attempt": attempt, "attempt_history": history}

        self.final.unlink(missing_ok=True)
        self.manifest.unlink(missing_ok=True)
        self._log("FAILED: retry budget exhausted; no master promoted")
        return {"ok": False, "error": "EXHAUSTED_RETRIES", "attempt_history": history}
