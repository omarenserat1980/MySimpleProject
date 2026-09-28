#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cinematic_image_engine_v51.orchestrator import ImageFactory

OUT = ROOT / "cinematic_output" / "electronic_brain_5s"
PROJECT = ROOT / "projects" / "electronic_brain_5s"
OUT.mkdir(parents=True, exist_ok=True)

BRIEF = os.environ.get(
    "EB_5S_BRIEF",
    "A lone futuristic hero stands on a rain-soaked rooftop at night, distant city lights, "
    "mist drifting through the skyline, cape moving gently in the wind, determined expression, "
    "photorealistic cinematic blockbuster cinematography, dramatic practical lighting, 35mm lens, "
    "shallow depth of field, realistic skin and materials, no text, no logos."
)

def main():
    if not shutil_which("ffmpeg"):
        raise SystemExit("ERROR: ffmpeg is not available to the BRAIN runtime.")
    if not shutil_which("ffprobe"):
        raise SystemExit("ERROR: ffprobe is not available to the BRAIN runtime.")

    os.environ["BRAIN_RUNTIME"] = "BRAIN_TERMUX_EMULATOR"
    os.environ["EB_IMAGE_ADAPTER"] = os.environ.get(
        "EB_IMAGE_ADAPTER",
        os.environ.get("BRAIN_EMULATOR_DIFFUSION_BIN", "")
    )
    os.environ["EB_DIFFUSION_MODEL"] = os.environ.get("EB_DIFFUSION_MODEL", "cyberrealistic-lcm")

    factory = ImageFactory(PROJECT, max_retries=3)
    state = factory.initialize("EB-5S")
    shot_id = "SC0001_001"
    state.shots = {shot_id: {
        "shot_id": shot_id, "scene_id": "SC0001",
        "purpose": "single five-second hero shot", "characters": ["hero"],
        "location": "rain-soaked futuristic rooftop at night", "action": BRIEF,
        "camera": "medium", "lens": "35mm", "emotion": "determined",
        "status": "PENDING", "attempts": 0,
    }}
    state.operations["FIVE_SECOND_FILM_REQUEST"] = "AUTHORIZED"
    factory.state_mgr.save(state)
    state = factory.run(state)
    master = Path(state.shots[shot_id].get("master_file", ""))
    if state.status != "COMPLETE" or not master.is_file():
        raise SystemExit(json.dumps({"status":"FAILED_IMAGE_STAGE","state":state.status,"manifest":str(PROJECT/"manifest.json")}, ensure_ascii=False))

    video = OUT / "electronic_brain_5s.mp4"
    vf = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,zoompan=z='min(zoom+0.0007,1.07)':d=120:s=1280x720:fps=24,fade=t=in:st=0:d=0.30,fade=t=out:st=4.70:d=0.30"
    cmd = ["ffmpeg","-y","-hide_banner","-loglevel","error","-loop","1","-i",str(master),"-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-vf",vf,"-t","5","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-ar","48000","-b:a","128k","-shortest","-movflags","+faststart",str(video)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode: raise SystemExit(p.stderr[-3000:])

    probe = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height","-of","json",str(video)], capture_output=True, text=True)
    if probe.returncode: raise SystemExit(probe.stderr[-2000:])
    data = json.loads(probe.stdout or "{}")
    duration = float((data.get("format") or {}).get("duration") or 0)
    streams = data.get("streams") or []
    ok = abs(duration-5.0) <= 0.10 and any(s.get("codec_type")=="video" for s in streams)
    result = {"status":"COMPLETE" if ok else "QC_FAILED","duration_s":duration,"video":str(video),"master_image":str(master),"project":str(PROJECT),"runtime":"BRAIN_TERMUX_EMULATOR","model":os.environ["EB_DIFFUSION_MODEL"]}
    (OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if ok else 2

def shutil_which(name):
    import shutil
    return shutil.which(name)

if __name__ == "__main__":
    raise SystemExit(main())
