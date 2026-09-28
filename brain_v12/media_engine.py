"""BRAIN Media Engine: a safe, allowlisted FFmpeg orchestration layer.

This module intentionally does not accept arbitrary FFmpeg flags or shell strings.
All commands are built from validated operation parameters and all media paths are
confined to the Brain media workspace.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from typing import Any
from uuid import uuid4


MEDIA_ROOT = pathlib.Path(os.getenv("BRAIN_MEDIA_ROOT", pathlib.Path(__file__).resolve().parent / "web" / "media")).resolve()
OUTPUT_ROOT = (MEDIA_ROOT / "engine").resolve()
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
MAX_INPUTS = 50
MAX_DURATION = int(os.getenv("BRAIN_MEDIA_MAX_DURATION_SECONDS", "3600"))
MAX_OUTPUT_BYTES = int(os.getenv("BRAIN_MEDIA_MAX_OUTPUT_BYTES", str(1024 * 1024 * 1024)))
MAX_WORKERS = max(1, min(int(os.getenv("BRAIN_MEDIA_WORKERS", "1")), 4))

_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="brain-media")
_lock = threading.RLock()
_jobs: dict[str, dict[str, Any]] = {}


def _now() -> float:
    return round(time.time(), 3)


def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name.upper()}_NOT_INSTALLED")
    return path


def _safe_name(name: str) -> str:
    base = pathlib.Path(str(name)).name
    if not base or base in {".", ".."} or base != str(name).replace("\\", "/").split("/")[-1]:
        raise ValueError("INVALID_MEDIA_NAME")
    if any(ord(ch) < 32 for ch in base):
        raise ValueError("INVALID_MEDIA_NAME")
    return base


def _resolve_input(name: str) -> pathlib.Path:
    base = _safe_name(name)
    path = (MEDIA_ROOT / base).resolve()
    if MEDIA_ROOT not in path.parents:
        raise ValueError("MEDIA_PATH_OUTSIDE_WORKSPACE")
    if not path.is_file():
        raise FileNotFoundError(f"MEDIA_NOT_FOUND:{base}")
    return path


def _output_path(operation: str, extension: str = "mp4") -> pathlib.Path:
    stamp = int(time.time() * 1000)
    return OUTPUT_ROOT / f"brain-{operation}-{stamp}-{uuid4().hex[:8]}.{extension}"


def _run(cmd: list[str], job_id: str) -> tuple[int, str]:
    started = _now()
    with _lock:
        _jobs[job_id]["command"] = cmd[0:2] + ["<validated-args>"]
        _jobs[job_id]["started_at"] = started
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            lines.append(line[-2000:])
            with _lock:
                _jobs[job_id]["logs"] = lines[-80:]
    rc = proc.wait()
    return rc, "\n".join(lines[-80:])


def _update(job_id: str, **fields: Any) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)


def _progress_from_log(line: str) -> int | None:
    if "time=" not in line:
        return None
    return None


def _execute(job_id: str, operation: str, spec: dict[str, Any]) -> None:
    _update(job_id, status="PREPARING", progress=5)
    try:
        ffmpeg = _tool("ffmpeg")
        ffprobe = _tool("ffprobe")
        output: pathlib.Path

        if operation == "probe":
            src = _resolve_input(spec["input"])
            proc = subprocess.run(
                [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(src)],
                capture_output=True, text=True, timeout=60, check=False,
            )
            if proc.returncode:
                raise RuntimeError(proc.stderr[-2000:] or "FFPROBE_FAILED")
            payload = json.loads(proc.stdout or "{}")
            _update(job_id, status="COMPLETED", progress=100, result=payload, finished_at=_now())
            return

        _update(job_id, status="PROCESSING", progress=15)

        if operation == "convert":
            src = _resolve_input(spec["input"])
            output = _output_path("convert", spec.get("format", "mp4"))
            fmt = spec.get("format", "mp4")
            if fmt not in {"mp4", "webm", "mov", "mkv"}:
                raise ValueError("UNSUPPORTED_OUTPUT_FORMAT")
            width = int(spec.get("width") or 0)
            height = int(spec.get("height") or 0)
            fps = float(spec.get("fps") or 0)
            bitrate = str(spec.get("bitrate") or "").strip()
            video_codec = {"mp4": "libx264", "mov": "libx264", "mkv": "libx264", "webm": "libvpx-vp9"}[fmt]
            audio_codec = "libopus" if fmt == "webm" else "aac"
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", str(src)]
            if width and height:
                if width > 3840 or height > 2160 or width % 2 or height % 2:
                    raise ValueError("INVALID_RESOLUTION")
                cmd += ["-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"]
            if fps:
                if not 1 <= fps <= 120:
                    raise ValueError("INVALID_FPS")
                cmd += ["-r", str(fps)]
            if bitrate:
                if not bitrate.endswith(("k", "M")) or not bitrate[:-1].replace(".", "", 1).isdigit():
                    raise ValueError("INVALID_BITRATE")
                cmd += ["-b:v", bitrate]
            cmd += ["-c:v", video_codec, "-c:a", audio_codec, "-movflags", "+faststart"] if fmt in {"mp4", "mov"} else ["-c:v", video_codec, "-c:a", audio_codec]
            cmd += [str(output)]

        elif operation == "extract-audio":
            src = _resolve_input(spec["input"])
            output = _output_path("audio", "mp3")
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", str(src), "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(output)]

        elif operation == "extract-frames":
            src = _resolve_input(spec["input"])
            output = _output_path("frame", "jpg")
            fps = float(spec.get("fps") or 1)
            if not 0.1 <= fps <= 10:
                raise ValueError("INVALID_FRAME_FPS")
            stem = output.with_suffix("")
            output_pattern = str(stem) + "-%05d.jpg"
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", str(src), "-vf", f"fps={fps}", "-frames:v", str(min(int(spec.get("count") or 30), 300)), output_pattern]

        elif operation == "concat":
            names = spec.get("inputs") or []
            if not isinstance(names, list) or not 2 <= len(names) <= MAX_INPUTS:
                raise ValueError("CONCAT_REQUIRES_2_TO_50_INPUTS")
            paths = [_resolve_input(x) for x in names]
            output = _output_path("concat", "mp4")
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, dir=str(OUTPUT_ROOT)) as fh:
                list_file = pathlib.Path(fh.name)
                for path in paths:
                    fh.write("file " + json.dumps(str(path)) + "\n")
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(output)]
        elif operation == "slideshow":
            names = spec.get("inputs") or []
            if not isinstance(names, list) or not 1 <= len(names) <= 30:
                raise ValueError("SLIDESHOW_REQUIRES_1_TO_30_IMAGES")
            paths = [_resolve_input(x) for x in names]
            duration = float(spec.get("duration") or 3)
            if not 0.5 <= duration <= 30:
                raise ValueError("INVALID_SLIDE_DURATION")
            output = _output_path("slideshow", "mp4")
            inputs: list[str] = []
            filters: list[str] = []
            for i, path in enumerate(paths):
                inputs += ["-loop", "1", "-t", str(duration), "-i", str(path)]
                filters.append(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p[v{i}]")
            concat_inputs = "".join(f"[v{i}]" for i in range(len(paths)))
            filters.append(f"{concat_inputs}concat=n={len(paths)}:v=1:a=0[vout]")
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning"] + inputs + ["-filter_complex", ";".join(filters), "-map", "[vout]", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
        else:
            raise ValueError("UNSUPPORTED_MEDIA_OPERATION")

        rc, logs = _run(cmd, job_id)
        if operation == "concat":
            try:
                list_file.unlink(missing_ok=True)
            except Exception:
                pass
        if rc != 0:
            raise RuntimeError("FFMPEG_FAILED")
        outputs = [output] if operation != "extract-frames" else sorted(OUTPUT_ROOT.glob(output.stem + "-*.jpg"))
        for item in outputs:
            if item.exists() and item.stat().st_size > MAX_OUTPUT_BYTES:
                item.unlink(missing_ok=True)
                raise RuntimeError("MEDIA_OUTPUT_TOO_LARGE")
        _update(
            job_id,
            status="QC",
            progress=92,
            result={"operation": operation, "outputs": ["/media/engine/" + x.name for x in outputs], "log_tail": logs[-4000:]},
        )
        qc = {"ok": True, "files": len(outputs), "outputs": [x.name for x in outputs]}
        if outputs and operation != "extract-frames":
            probe = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration,size,format_name", "-of", "json", str(outputs[0])],
                capture_output=True, text=True, timeout=30, check=False,
            )
            qc["probe_ok"] = probe.returncode == 0
            if probe.returncode == 0:
                qc["metadata"] = json.loads(probe.stdout or "{}")
        _update(job_id, status="COMPLETED", progress=100, qc=qc, finished_at=_now())
    except Exception as exc:
        _update(job_id, status="FAILED", progress=100, error=str(exc), finished_at=_now())


def submit(operation: str, spec: dict[str, Any]) -> dict[str, Any]:
    allowed = {"probe", "convert", "concat", "extract-audio", "extract-frames", "slideshow"}
    if operation not in allowed:
        raise ValueError("UNSUPPORTED_MEDIA_OPERATION")
    job_id = uuid4().hex
    job = {
        "job_id": job_id, "operation": operation, "status": "QUEUED", "progress": 0,
        "created_at": _now(), "started_at": None, "finished_at": None,
        "result": None, "qc": None, "error": None, "logs": [], "command": None,
    }
    with _lock:
        _jobs[job_id] = job
    _pool.submit(_execute, job_id, operation, spec)
    return snapshot(job_id)


def snapshot(job_id: str) -> dict[str, Any]:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return {"ok": False, "status": "NOT_FOUND", "job_id": job_id}
        return {"ok": True, **asdict(_JobView(job))}


def list_jobs(limit: int = 30) -> list[dict[str, Any]]:
    with _lock:
        ids = list(_jobs.keys())[-max(1, min(limit, 100)):]
    return [snapshot(x) for x in reversed(ids)]


@dataclass
class _JobView:
    job_id: str
    operation: str
    status: str
    progress: int
    created_at: float
    started_at: float | None
    finished_at: float | None
    result: Any
    qc: Any
    error: str | None
    logs: list[str]
    command: list[str] | None

    def __init__(self, job: dict[str, Any]):
        for field in self.__dataclass_fields__:
            setattr(self, field, job.get(field))
