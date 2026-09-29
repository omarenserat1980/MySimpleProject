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
from . import brain_ffmpeg
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
MAX_WORKERS = max(1, min(int(os.getenv("BRAIN_MEDIA_WORKERS", "2")), 4))

_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="brain-media")
_lock = threading.RLock()
_jobs: dict[str, dict[str, Any]] = {}
_processes: dict[str, subprocess.Popen] = {}


def _now() -> float:
    return round(time.time(), 3)


def _tool(name: str) -> str:
    if name == "ffmpeg":
        return brain_ffmpeg.ffmpeg()
    if name == "ffprobe":
        return brain_ffmpeg.ffprobe()
    raise RuntimeError(f"UNSUPPORTED_MEDIA_TOOL:{name}")


def _safe_name(name: str) -> str:
    raw = str(name).strip().replace("\\", "/")
    base = pathlib.PurePosixPath(raw).name
    if not raw or raw in {".", ".."} or "/" in raw or base != raw:
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
    with _lock:
        _jobs[job_id]["command"] = cmd[0:2] + ["<validated-args>"]
        _jobs[job_id]["started_at"] = _now()
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    with _lock:
        _processes[job_id] = proc
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            lines.append(line[-2000:])
            with _lock:
                _jobs[job_id]["logs"] = lines[-80:]
    rc = proc.wait()
    with _lock:
        _processes.pop(job_id, None)
    return rc, "\n".join(lines[-80:])


def _update(job_id: str, **fields: Any) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)


def _validate_transition(value: Any) -> str:
    value = str(value or "none").lower()
    if value not in {"none", "fade", "wipeleft", "wiperight", "slideleft", "slideright"}:
        raise ValueError("UNSUPPORTED_TRANSITION")
    return value


def _drawtext_escape(value: Any) -> str:
    text = str(value or "")
    if len(text) > 300:
        raise ValueError("TIMELINE_TEXT_TOO_LONG")
    return text.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'").replace("%", r"\%")


def _timeline_command(spec: dict[str, Any], ffmpeg: str) -> tuple[list[str], pathlib.Path]:
    scenes = spec.get("scenes") or []
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= MAX_INPUTS:
        raise ValueError("TIMELINE_REQUIRES_1_TO_50_SCENES")
    output = _output_path("timeline", "mp4")
    profiles = {
        "youtube_1080p": (1920, 1080, 30),
        "shorts_1080x1920": (1080, 1920, 30),
        "cinematic_4k": (3840, 2160, 24),
    }
    profile = str(spec.get("profile") or "youtube_1080p")
    if profile not in profiles:
        raise ValueError("UNSUPPORTED_CINEMATIC_PROFILE")
    width, height, fps = profiles[profile]
    inputs: list[str] = []
    filters: list[str] = []
    video_labels: list[str] = []
    audio_labels: list[str] = []
    durations: list[float] = []
    ffprobe = _tool("ffprobe")
    input_index = 0

    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError("INVALID_TIMELINE_SCENE")
        src = _resolve_input(scene.get("input", ""))
        start = float(scene.get("start") or 0)
        duration = float(scene.get("duration") or 0)
        if start < 0 or duration <= 0 or duration > 1800:
            raise ValueError("INVALID_TIMELINE_SCENE_RANGE")
        durations.append(duration)
        inputs += ["-ss", str(start), "-t", str(duration), "-i", str(src)]
        vi = input_index
        input_index += 1
        v, a = f"v{i}", f"a{i}"
        vf = (
            f"[{vi}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p"
        )
        caption = scene.get("caption")
        if caption:
            vf += f",drawtext=text='{_drawtext_escape(caption)}':x=(w-text_w)/2:y=h-120:fontsize=46:fontcolor=white:borderw=3:bordercolor=black"
        filters.append(vf + f"[{v}]")

        probe = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index", "-of", "csv=p=0", str(src)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if probe.returncode == 0 and probe.stdout.strip():
            filters.append(f"[{vi}:a]aresample=48000,asetpts=N/SR/TB[{a}]")
        else:
            ai = input_index
            inputs += ["-f", "lavfi", "-t", str(duration), "-i", "anullsrc=r=48000:cl=stereo"]
            input_index += 1
            filters.append(f"[{ai}:a]atrim=duration={duration},asetpts=PTS-STARTPTS[{a}]")
        video_labels.append(v)
        audio_labels.append(a)

    watermark = str(spec.get("watermark") or "").strip()
    if watermark:
        wp = _resolve_input(watermark)
        wi = input_index
        inputs += ["-loop", "1", "-i", str(wp)]
        input_index += 1
        filters.append(f"[{wi}:v]scale=320:-1,format=rgba[wm0]")
        # A filter output label is single-use in FFmpeg. Split it so the watermark
        # can be applied independently to every scene.
        wm_splits = "".join(f"[wm{i}]" for i in range(len(video_labels)))
        filters.append(f"[wm0]split={len(video_labels)}{wm_splits}")
        for i, label in enumerate(list(video_labels)):
            wmout = f"vw{i}"
            filters.append(f"[{label}][wm{i}]overlay=W-w-35:H-h-35:shortest=1[{wmout}]")
            video_labels[i] = wmout

    global_audio_files = []
    for key, default_volume in (("music", 0.35), ("voiceover", 1.0)):
        name = str(spec.get(key) or "").strip()
        if name:
            global_audio_files.append((name, float(spec.get(key + "_volume") or default_volume)))
    global_audio_label = None
    if global_audio_files:
        extras = []
        for name, volume in global_audio_files:
            path = _resolve_input(name)
            inputs += ["-stream_loop", "-1", "-i", str(path)]
            idx = input_index
            input_index += 1
            label = f"ga{idx}"
            filters.append(f"[{idx}:a]volume={volume},aresample=48000[{label}]")
            extras.append(label)
        joined = "".join(f"[{x}]" for x in extras)
        global_audio_label = "global_audio"
        filters.append(f"{joined}amix=inputs={len(extras)}:duration=longest:dropout_transition=2[{global_audio_label}]")

    transition = _validate_transition(spec.get("transition", "none"))
    if transition == "none" or len(video_labels) == 1:
        if len(video_labels) == 1:
            filters += [f"[{video_labels[0]}]null[vout]", f"[{audio_labels[0]}]anull[aout]"]
        else:
            filters += [
                f"{''.join(f'[{x}]' for x in video_labels)}concat=n={len(video_labels)}:v=1:a=0[vout]",
                f"{''.join(f'[{x}]' for x in audio_labels)}concat=n={len(audio_labels)}:v=0:a=1[aout]",
            ]
    else:
        current_v, current_a = video_labels[0], audio_labels[0]
        offset = durations[0]
        for i in range(1, len(video_labels)):
            trans = min(float(spec.get("transition_duration") or 0.6), durations[i] / 2, durations[i - 1] / 2)
            if trans <= 0:
                raise ValueError("INVALID_TRANSITION_DURATION")
            vout, aout = f"vx{i}", f"ax{i}"
            filters.append(f"[{current_v}][{video_labels[i]}]xfade=transition={transition}:duration={trans}:offset={max(0, offset-trans)}[{vout}]")
            filters.append(f"[{current_a}][{audio_labels[i]}]acrossfade=d={trans}:c1=tri:c2=tri[{aout}]")
            current_v, current_a = vout, aout
            offset += durations[i] - trans
        filters += [f"[{current_v}]null[vout]", f"[{current_a}]anull[aout]"]

    if global_audio_label:
        filters.append(f"[aout][{global_audio_label}]amix=inputs=2:duration=first:dropout_transition=2[aout_final]")
        audio_output_label = "aout_final"
    else:
        audio_output_label = "aout"

    preset = str(spec.get("preset") or "medium")
    if preset not in {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"}:
        raise ValueError("UNSUPPORTED_ENCODER_PRESET")
    crf = max(18, min(int(spec.get("crf") or 20), 30))
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning"] + inputs
    cmd += [
        "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", f"[{audio_output_label}]",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)
    ]
    return cmd, output


def _execute(job_id: str, operation: str, spec: dict[str, Any]) -> None:
    _update(job_id, status="PREPARING", progress=5)
    try:
        ffmpeg, ffprobe = _tool("ffmpeg"), _tool("ffprobe")
        output: pathlib.Path

        if operation == "probe":
            src = _resolve_input(spec["input"])
            proc = subprocess.run(
                [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(src)],
                capture_output=True, text=True, timeout=60, check=False,
            )
            if proc.returncode:
                raise RuntimeError(proc.stderr[-2000:] or "FFPROBE_FAILED")
            _update(job_id, status="COMPLETED", progress=100, result=json.loads(proc.stdout or "{}"), finished_at=_now())
            return

        _update(job_id, status="PROCESSING", progress=15)

        if operation == "timeline":
            cmd, output = _timeline_command(spec, ffmpeg)
        elif operation == "convert":
            src = _resolve_input(spec["input"])
            fmt = str(spec.get("format") or "mp4").lower()
            if fmt not in {"mp4", "webm", "mov", "mkv"}:
                raise ValueError("UNSUPPORTED_OUTPUT_FORMAT")
            output = _output_path("convert", fmt)
            width, height, fps = int(spec.get("width") or 0), int(spec.get("height") or 0), float(spec.get("fps") or 0)
            bitrate = str(spec.get("bitrate") or "").strip()
            if width or height:
                if not (width and height) or width > 3840 or height > 2160 or width % 2 or height % 2:
                    raise ValueError("INVALID_RESOLUTION")
            if fps and not 1 <= fps <= 120:
                raise ValueError("INVALID_FPS")
            if bitrate and (not bitrate.endswith(("k", "M")) or not bitrate[:-1].replace(".", "", 1).isdigit()):
                raise ValueError("INVALID_BITRATE")
            video_codec = {"mp4": "libx264", "mov": "libx264", "mkv": "libx264", "webm": "libvpx-vp9"}[fmt]
            audio_codec = "libopus" if fmt == "webm" else "aac"
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", str(src)]
            if width and height:
                cmd += ["-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"]
            if fps:
                cmd += ["-r", str(fps)]
            if bitrate:
                cmd += ["-b:v", bitrate]
            cmd += ["-c:v", video_codec, "-c:a", audio_codec]
            if fmt in {"mp4", "mov"}:
                cmd += ["-movflags", "+faststart"]
            cmd += [str(output)]
        elif operation == "extract-audio":
            src = _resolve_input(spec["input"])
            output = _output_path("audio", "mp3")
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", str(src), "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(output)]
        elif operation == "extract-frames":
            src = _resolve_input(spec["input"])
            output = _output_path("frame", "jpg")
            fps = float(spec.get("fps") or 1)
            count = int(spec.get("count") or 30)
            if not 0.1 <= fps <= 10 or not 1 <= count <= 300:
                raise ValueError("INVALID_FRAME_SETTINGS")
            pattern = str(output.with_suffix("")) + "-%05d.jpg"
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", str(src), "-vf", f"fps={fps}", "-frames:v", str(count), pattern]
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
        elif operation == "trim":
            src = _resolve_input(spec["input"])
            start, duration = float(spec.get("start") or 0), float(spec.get("duration") or 0)
            if start < 0 or duration <= 0 or start > MAX_DURATION or duration > MAX_DURATION:
                raise ValueError("INVALID_TRIM_RANGE")
            output = _output_path("trim", "mp4")
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-ss", str(start), "-i", str(src), "-t", str(duration), "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(output)]
        elif operation == "mix-audio":
            video, audio = _resolve_input(spec["video"]), _resolve_input(spec["audio"])
            output = _output_path("mix-audio", "mp4")
            volume = float(spec.get("volume") or 1)
            if not 0 <= volume <= 3:
                raise ValueError("INVALID_AUDIO_VOLUME")
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", str(video), "-i", str(audio), "-filter_complex", f"[1:a]volume={volume}[a]", "-map", "0:v:0", "-map", "[a]", "-shortest", "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart", str(output)]
        elif operation == "fade":
            src = _resolve_input(spec["input"])
            fade_in, fade_out, duration = float(spec.get("fade_in") or 0), float(spec.get("fade_out") or 0), float(spec.get("duration") or 0)
            if min(fade_in, fade_out) < 0 or max(fade_in, fade_out) > 30 or duration <= 0:
                raise ValueError("INVALID_FADE")
            output = _output_path("fade", "mp4")
            filters = []
            if fade_in:
                filters.append(f"fade=t=in:st=0:d={fade_in}")
            if fade_out:
                filters.append(f"fade=t=out:st={max(0, duration-fade_out)}:d={fade_out}")
            if not filters:
                filters.append("null")
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", str(src), "-vf", ",".join(filters), "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(output)]
        elif operation == "slideshow":
            names = spec.get("inputs") or []
            if not isinstance(names, list) or not 1 <= len(names) <= 30:
                raise ValueError("SLIDESHOW_REQUIRES_1_TO_30_IMAGES")
            paths = [_resolve_input(x) for x in names]
            duration = float(spec.get("duration") or 3)
            if not 0.5 <= duration <= 30:
                raise ValueError("INVALID_SLIDE_DURATION")
            output = _output_path("slideshow", "mp4")
            inputs, filters = [], []
            for i, path in enumerate(paths):
                inputs += ["-loop", "1", "-t", str(duration), "-i", str(path)]
                filters.append(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p[v{i}]")
            filters.append(f"{''.join(f'[v{i}]' for i in range(len(paths)))}concat=n={len(paths)}:v=1:a=0[vout]")
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
        _update(job_id, status="QC", progress=92, result={"operation": operation, "outputs": ["/media/engine/" + x.name for x in outputs], "log_tail": logs[-4000:]})
        qc = {"ok": True, "files": len(outputs), "outputs": [x.name for x in outputs]}
        if outputs and operation != "extract-frames":
            probe = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration,size,format_name", "-of", "json", str(outputs[0])], capture_output=True, text=True, timeout=30, check=False)
            qc["probe_ok"] = probe.returncode == 0
            if probe.returncode == 0:
                qc["metadata"] = json.loads(probe.stdout or "{}")
        _update(job_id, status="COMPLETED", progress=100, qc=qc, finished_at=_now())
    except Exception as exc:
        _update(job_id, status="FAILED", progress=100, error=str(exc), finished_at=_now())


def cancel(job_id: str) -> dict[str, Any]:
    with _lock:
        job = _jobs.get(job_id)
        proc = _processes.get(job_id)
        if not job:
            return {"ok": False, "status": "NOT_FOUND", "job_id": job_id}
        if job["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            return snapshot(job_id)
        if proc is None:
            job["status"], job["finished_at"], job["progress"] = "CANCELLED", _now(), 100
            return snapshot(job_id)
        job["status"] = "CANCELLING"
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    _update(job_id, status="CANCELLED", progress=100, finished_at=_now(), error="CANCELLED_BY_USER")
    return snapshot(job_id)


def submit(operation: str, spec: dict[str, Any]) -> dict[str, Any]:
    operation = str(operation).strip().lower()
    allowed = {"probe", "convert", "concat", "extract-audio", "extract-frames", "slideshow", "trim", "mix-audio", "fade", "timeline"}
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
