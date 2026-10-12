"""Brain-native media toolchain resolver.

Production media code must use the Brain-provided FFmpeg/FFprobe toolchain.
Production has no fallback to host/system binaries; CI may use a runner-installed tool.
Configure BRAIN_FFMPEG_BIN and BRAIN_FFPROBE_BIN, or package executables at
brain_v12/bin/ffmpeg and brain_v12/bin/ffprobe.
"""
from __future__ import annotations
import os
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent
BIN_ROOT = ROOT / "bin"

def _resolve(env_name: str, filename: str) -> str:
    configured = os.getenv(env_name, "").strip()
    candidates = []
    if configured:
        candidates.append(pathlib.Path(configured))
    candidates.append(BIN_ROOT / filename)
    # Termux/Android native toolchain: keep media execution on-device without
    # leaking the Termux PATH into Android-shell processes.
    termux_tool = pathlib.Path("/data/data/com.termux/files/usr/bin") / filename
    if termux_tool.is_file():
        candidates.append(termux_tool)
    if os.getenv("CI", "").lower() == "true":
        system_path = shutil.which(filename)
        if system_path:
            candidates.append(pathlib.Path(system_path))
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    raise RuntimeError(
        f"{env_name}_NOT_CONFIGURED_OR_EXECUTABLE; "
        f"Brain toolchain required: set {env_name} or package {BIN_ROOT / filename}"
    )

def ffmpeg() -> str:
    return _resolve("BRAIN_FFMPEG_BIN", "ffmpeg")

def ffprobe() -> str:
    return _resolve("BRAIN_FFPROBE_BIN", "ffprobe")

def diagnostics() -> dict:
    result = {}
    for key, fn in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)):
        try:
            result[key] = {"ok": True, "path": fn()}
        except Exception as exc:
            result[key] = {"ok": False, "error": str(exc)}
    result["source"] = "brain-native-toolchain"
    return result
