from __future__ import annotations
import os, shutil
from pathlib import Path

COMMON_EXECUTABLES = (
    "eb-image-generator",
    "stable-diffusion",
    "stable-diffusion.cpp",
    "sd-cli",
    "comfy",
    "comfyui",
    "python",
    "termux-diffusion",
)

def discover_runtime(config=None):
    config = config or {}
    configured = os.environ.get("EB_IMAGE_ADAPTER")
    candidates = []
    if configured:
        candidates.append({"executable": configured, "source": "env"})
    for item in config.get("adapters", []):
        exe = item.get("executable") if isinstance(item, dict) else str(item)
        if exe:
            candidates.append({"executable": exe, "source": "config"})
    for name in COMMON_EXECUTABLES:
        found = shutil.which(name)
        if found:
            candidates.append({"executable": found, "source": "PATH"})
    seen = set()
    result = []
    for item in candidates:
        exe = item["executable"]
        if exe in seen:
            continue
        seen.add(exe)
        if os.path.isfile(exe) and os.access(exe, os.X_OK):
            result.append(item)
    return result

def device_profile():
    try:
        ram_mb = int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 / 1024)
    except Exception:
        ram_mb = 0
    try:
        free_mb = int(shutil.disk_usage(Path.home()).free / 1024 / 1024)
    except Exception:
        free_mb = 0
    return {
        "ram_mb": ram_mb,
        "storage_free_mb": free_mb,
        "termux": Path("/data/data/com.termux/files/usr").exists(),
        "android": os.environ.get("ANDROID_ROOT") is not None,
    }
