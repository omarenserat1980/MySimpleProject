#!/usr/bin/env python3
"""BRAIN Machine Cinema Factory.

Provider-free cinematic production from Brain machine-raster frames and FFmpeg.
Default contract: 120 minutes = 240 x 30-second verified shots.
Override BRAIN_FILM_PARTS / BRAIN_FILM_PART_SECONDS for controlled runs.
"""
from __future__ import annotations
import json, os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("BRAIN_MACHINE_FILM_ROOT", ROOT / "brain6_artifacts" / "machine_films"))
FPS = int(os.environ.get("BRAIN_FILM_FPS", "24"))
PARTS = max(1, int(os.environ.get("BRAIN_FILM_PARTS", "240")))
PART_SECONDS = max(5, int(os.environ.get("BRAIN_FILM_PART_SECONDS", "30")))
START_PART = max(1, int(os.environ.get("BRAIN_FILM_START", "1")))
END_PART = min(PARTS, int(os.environ.get("BRAIN_FILM_END", str(PARTS))))
W, H = 1000, 650

SHOTS = [
    ("الفجر", "landscape", "sunrise"), ("الطريق", "car", "road"),
    ("المدينة", "city", "city"), ("المطر", "green_mask", "rain"),
    ("الروبوت", "robot", "city"), ("البحيرة", "landscape", "lake"),
    ("البرج", "city", "tower"), ("الغابة", "landscape", "forest"),
    ("القناع", "green_mask", "magic"), ("الليل", "landscape", "night"),
    ("المطاردة", "car", "highway"), ("السطح", "green_mask", "rooftop"),
]

def scene_for(i, title, typ, extra):
    palette = "night" if i % 5 == 0 or extra == "night" else ("sunset" if i % 7 == 0 else "default")
    words = {"landscape":"منظر طبيعي سينمائي","city":"مدينة سينمائية","car":"مطاردة سيارة سينمائية",
             "robot":"روبوت سينمائي","green_mask":"بطل القناع الأخضر في مشهد سينمائي"}
    prompt = f"{words[typ]}: {title} {extra}; لقطة فيلمية واسعة، إضاءة درامية، عمق بصري، حركة كاميرا بطيئة"
    from brain_v12 import visual_engine
    from brain_v12.machine_raster_engine import render_machine
    scene = visual_engine.compile_scene(prompt, typ)
    scene["palette"] = palette
    png, commands = render_machine(scene)
    return scene, png, commands

def run(cmd, timeout=600):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-4000:])
    return p

def render_part(i, png):
    part = OUT / "parts" / f"{i:03d}"; part.mkdir(parents=True, exist_ok=True)
    img = part / "machine.png"; img.write_bytes(png)
    mp4 = part / f"part-{i:03d}.mp4"
    frames = PART_SECONDS * FPS
    vf = f"zoompan=z='min(zoom+0.0009,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p"
    audio = "amix=inputs=2:duration=longest,volume=0.18"
    run(["ffmpeg","-y","-loop","1","-i",str(img),
         "-f","lavfi","-i",f"sine=frequency={55+(i%8)*11}:sample_rate=48000:duration={PART_SECONDS}",
         "-f","lavfi","-i",f"sine=frequency={110+(i%6)*22}:sample_rate=48000:duration={PART_SECONDS}",
         "-vf",vf,"-af",audio,"-t",str(PART_SECONDS),
         "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","192k","-shortest",str(mp4)],1200)
    return mp4

def qc(path):
    p = run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height","-of","json",str(path)],60)
    d=json.loads(p.stdout); streams=d.get("streams",[])
    return {"duration":float(d["format"]["duration"]),
            "video":any(s.get("codec_type")=="video" for s in streams),
            "width":next((s.get("width") for s in streams if s.get("codec_type")=="video"),None),
            "height":next((s.get("height") for s in streams if s.get("codec_type")=="video"),None)}

def build_film(title="BRAIN — فيلم سينمائي طويل 120 دقيقة"):
    OUT.mkdir(parents=True, exist_ok=True)
    target=PARTS*PART_SECONDS
    manifest={"title":title,"renderer":"Brain Machine Raster Painter",
              "binary_model":"integer pixel operations + PNG bytes","parts":PARTS,
              "part_seconds":PART_SECONDS,"target_seconds":target,"fps":FPS,"parts_manifest":[]}
    clips=[]
    if START_PART > END_PART:
        raise ValueError(f"invalid_part_range:{START_PART}:{END_PART}")
    for i in range(START_PART,END_PART+1):
        title0,typ,extra=SHOTS[(i-1)%len(SHOTS)]
        scene,png,commands=scene_for(i,title0,typ,extra)
        clip=render_part(i,png); q=qc(clip)
        if not(q["video"] and PART_SECONDS-1<=q["duration"]<=PART_SECONDS+1 and q["width"]==W and q["height"]==H):
            raise RuntimeError(f"PART_QC_FAILED:{i}:{q}")
        clips.append(clip)
        manifest["parts_manifest"].append({"part":i,"title":title0,"scene":scene,
            "machine_instruction_count":len(commands),"video":str(clip),"qc":q})
        (OUT/"manifest.partial.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    concat=OUT/"concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf-8")
    if START_PART != 1 or END_PART != PARTS or os.environ.get("BRAIN_FILM_SHARD_ONLY","0")=="1":
        manifest["status"]="SHARD_COMPLETED"
        manifest["range"]={"start":START_PART,"end":END_PART}
        manifest["final"]=None
        (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        return manifest
    final=OUT/"final.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(final)],3600)
    final_qc=qc(final); tolerance=max(2.0,min(10.0,target*0.01))
    if not(final_qc["video"] and abs(final_qc["duration"]-target)<=tolerance and final_qc["width"]==W and final_qc["height"]==H):
        raise RuntimeError(f"MASTER_QC_FAILED:{final_qc}")
    manifest["status"]="VERIFIED_COMPLETED"; manifest["final"]=str(final); manifest["master_qc"]=final_qc
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"VERIFIED_COMPLETED").write_text("BRAIN MACHINE CINEMA VERIFIED — 120 MINUTES\n",encoding="utf-8")
    return manifest

if __name__=="__main__":
    print(json.dumps(build_film(os.environ.get("BRAIN_FILM_TITLE","BRAIN — فيلم سينمائي طويل 120 دقيقة")),ensure_ascii=False,indent=2))
