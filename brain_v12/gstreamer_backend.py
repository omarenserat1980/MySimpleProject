"""GStreamer backend for BRAIN Media Engine.

The render path avoids FFmpeg. GStreamer/GES provides image-sequence video,
audio mixing, H.264/AAC encoding and timeline crossfades. The independent QC
oracle may still use FFmpeg until that layer is separately migrated.
"""
from __future__ import annotations
import math, shutil, subprocess
from pathlib import Path
from typing import Iterable

def _exe(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"GSTREAMER_REQUIRED:{name}")
    return path

def _run(cmd: list[str], timeout: int = 1200) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-6000:])
    return p

def available() -> bool:
    return bool(shutil.which("gst-launch-1.0") and shutil.which("ges-launch-1.0"))

def _make_motion_frames(image: Path, frame_dir: Path, frames: int, width: int, height: int) -> None:
    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("PIL_REQUIRED_FOR_GSTREAMER_MOTION_FRAMES") from exc
    src = Image.open(image).convert("RGB")
    sw, sh = src.size
    frame_dir.mkdir(parents=True, exist_ok=True)
    for n in range(frames):
        phase = n / max(frames - 1, 1)
        zoom = 1.0 + 0.08 * phase
        cw, ch = max(2, int(sw / zoom)), max(2, int(sh / zoom))
        left, top = max(0, (sw - cw) // 2), max(0, (sh - ch) // 2)
        frame = src.crop((left, top, left + cw, top + ch)).resize(
            (width, height), Image.Resampling.LANCZOS
        )
        frame.save(frame_dir / f"frame-{n:05d}.png", optimize=False)

def _make_tone(path: Path, duration: float, freq: int, kind: str) -> None:
    gst = _exe("gst-launch-1.0")
    samples = max(1, math.ceil(duration * 48000 / 1024))
    wave = "sine" if kind == "music" else "white-noise"
    cmd = [
        gst, "-e", "-q", "audiotestsrc", f"wave={wave}", f"freq={freq}",
        f"num-buffers={samples}", "samplesperbuffer=1024", "is-live=false", "!",
        "audioconvert", "!", "audioresample", "!",
        "audio/x-raw,format=S16LE,channels=2,rate=48000", "!",
        "wavenc", "!", "filesink", f"location={path}",
    ]
    _run(cmd, 180)

def render_part(image: Path, output: Path, duration: float, fps: int,
                width: int, height: int, voice: Path | None = None,
                music: Path | None = None, sfx: Path | None = None) -> Path:
    gst = _exe("gst-launch-1.0")
    frames = max(1, int(round(duration * fps)))
    work = output.parent / "gstreamer-frames"
    _make_motion_frames(image, work, frames, width, height)
    audio_paths = [p for p in (voice, music, sfx) if p and p.is_file()]
    if not audio_paths:
        raise RuntimeError("GSTREAMER_AUDIO_INPUT_REQUIRED")
    pipeline = (
        f'multifilesrc location="{work}/frame-%05d.png" start-index=0 '
        f'stop-index={frames-1} caps="image/png,framerate={fps}/1" ! pngdec ! videoconvert ! videoscale ! '
        f'video/x-raw,width={width},height={height},framerate={fps}/1 ! '
        'x264enc bitrate=1200 speed-preset=medium tune=zerolatency ! '
        'h264parse ! mux.video_0 '
    )
    for idx, path in enumerate(audio_paths):
        pipeline += (
            f'filesrc location="{path}" ! wavparse ! audioconvert ! audioresample ! '
            f'audio/x-raw,rate=48000,channels=2 ! queue ! mixer.sink_{idx} '
        )
    pipeline += (
        'audiomixer name=mixer latency=0 ! audioconvert ! audioresample ! '
        'voaacenc bitrate=192000 ! aacparse ! mux.audio_0 '
        f'mp4mux name=mux ! filesink location="{output}"'
    )
    _run([gst, "-e", pipeline], max(300, int(duration * 60) + 300))
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("GSTREAMER_RENDER_EMPTY")
    shutil.rmtree(work, ignore_errors=True)
    return output

def render_timeline(clips: Iterable[Path], output: Path, duration: float,
                    transition: float = 0.5) -> Path:
    ges = _exe("ges-launch-1.0")
    clips = list(clips)
    if not clips:
        raise ValueError("GSTREAMER_TIMELINE_EMPTY")
    # Use GES as the timeline engine through its Python GObject API when available.
    # This avoids relying on shell-only +clip/+transition syntax.
    try:
        import gi
        gi.require_version("GES", "1.0")
        from gi.repository import GES, Gst
    except Exception as exc:
        raise RuntimeError("GSTREAMER_GES_PYTHON_BINDINGS_REQUIRED") from exc
    Gst.init(None)
    GES.init()
    timeline = GES.Timeline.new()
    layer = GES.Layer.new()
    timeline.add_layer(layer)
    for i, clip in enumerate(clips):
        asset = GES.UriClipAsset.request_asset(clip.resolve().as_uri())
        ges_clip = layer.add_asset(asset, int((i * (duration - transition)) * Gst.SECOND),
                                   0, int(duration * Gst.SECOND), GES.TrackType.UNKNOWN)
        if ges_clip is None:
            raise RuntimeError(f"GSTREAMER_GES_ADD_CLIP_FAILED:{clip}")
    pipeline = GES.Pipeline.new("brain-master")
    pipeline.set_timeline(timeline)
    pipeline.set_state(Gst.State.PLAYING)
    bus = pipeline.get_bus()
    end = max(600, int((duration * len(clips)) * 60) + 600)
    import time
    deadline = time.time() + end
    while time.time() < deadline:
        msg = bus.timed_pop_filtered(Gst.SECOND, Gst.MessageType.ERROR | Gst.MessageType.EOS)
        if msg:
            if msg.type == Gst.MessageType.ERROR:
                err, dbg = msg.parse_error()
                pipeline.set_state(Gst.State.NULL)
                raise RuntimeError(f"GSTREAMER_GES_TIMELINE_ERROR:{err}:{dbg}")
            if msg.type == Gst.MessageType.EOS:
                break
    else:
        pipeline.set_state(Gst.State.NULL)
        raise RuntimeError("GSTREAMER_GES_TIMELINE_TIMEOUT")
    pipeline.set_state(Gst.State.NULL)
    # GES pipeline output is configured by the project render settings; verify it.
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("GSTREAMER_TIMELINE_EMPTY_OUTPUT")
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("GSTREAMER_TIMELINE_EMPTY_OUTPUT")
    return output
