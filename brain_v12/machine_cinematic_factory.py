#!/usr/bin/env python3
"""BRAIN 60-minute Machine Cinema Factory.

Generates a complete 60-minute film from deterministic machine-raster frames.
No SVG, Pillow, paid image APIs, or external image generator is required.

Contract:
  60 parts x 30 seconds = 1800 seconds.
  Each part gets a machine-raster PNG and an FFmpeg cinematic motion render.
  Final MP4 is accepted only after ffprobe duration/stream checks.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get("BRAIN_MACHINE_FILM_ROOT",ROOT/"brain6_artifacts"/"machine_films"))
FPS=int(os.environ.get("BRAIN_FILM_FPS","24"))
PARTS=60
PART_SECONDS=30
W,H=1000,650

SHOTS=[
("الفجر","landscape","sunrise"),("الطريق","car","road"),("المدينة","city","city"),
("المطر","green_mask","rain"),("الروبوت","robot","city"),("البحيرة","landscape","lake"),
("البرج","city","tower"),("الغابة","landscape","forest"),("القناع","green_mask","magic"),
("الليل","landscape","night"),("المطاردة","car","highway"),("السطح","green_mask","rooftop"),
]

def scene_for(i,title,typ,extra):
    palette="night" if i%5==0 or extra=="night" else ("sunset" if i%7==0 else "default")
    words={"landscape":"منظر طبيعي سينمائي","city":"مدينة سينمائية","car":"مطاردة سيارة سينمائية",
           "robot":"روبوت سينمائي","green_mask":"بطل القناع الأخضر في مشهد سينمائي"}[typ]
    prompt=f"{words}: {title} {extra}; لقطة فيلمية واسعة، إضاءة درامية، عمق بصري، حركة كاميرا بطيئة"
    from brain_v12 import visual_engine
    from brain_v12.machine_raster_engine import render_machine
    scene=visual_engine.compile_scene(prompt,typ)
    scene["palette"]=palette
    png,commands=render_machine(scene)
    return scene,png,commands

def run(cmd,timeout=600):
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-4000:])
    return p

def render_part(i,scene,png):
    part=OUT/"parts"/f"{i:03d}"; part.mkdir(parents=True,exist_ok=True)
    img=part/"machine.png"; img.write_bytes(png)
    mp4=part/f"part-{i:03d}.mp4"
    # One machine-rendered keyframe becomes a 30s shot with deterministic
    # Ken-Burns motion. FFmpeg encodes the numbered image into video.
    vf=f"zoompan=z='min(zoom+0.0009,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={PART_SECONDS*FPS}:s={W}x{H}:fps={FPS},format=yuv420p"
    audio="amix=inputs=2:duration=longest,volume=0.18"
    run(["ffmpeg","-y","-loop","1","-i",str(img),
         "-f","lavfi","-i",f"sine=frequency={55+(i%8)*11}:sample_rate=48000:duration={PART_SECONDS}",
         "-f","lavfi","-i",f"sine=frequency={110+(i%6)*22}:sample_rate=48000:duration={PART_SECONDS}",
         "-vf",vf,"-af",audio,"-t",str(PART_SECONDS),
         "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","192k","-shortest",str(mp4)],1200)
    return mp4

def qc(path):
    p=run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height",
           "-of","json",str(path)],60)
    d=json.loads(p.stdout); duration=float(d["format"]["duration"])
    streams=d.get("streams",[])
    video=any(s.get("codec_type")=="video" for s in streams)
    return {"duration":duration,"video":video,"width":next((s.get("width") for s in streams if s.get("codec_type")=="video"),None),
            "height":next((s.get("height") for s in streams if s.get("codec_type")=="video"),None)}

def build_film(title="BRAIN — فيلم الآلة"):
    OUT.mkdir(parents=True,exist_ok=True)
    manifest={"title":title,"renderer":"Brain Machine Raster Painter","binary_model":"integer pixel operations + PNG bytes",
              "parts":PARTS,"part_seconds":PART_SECONDS,"target_seconds":PARTS*PART_SECONDS,"fps":FPS,"parts_manifest":[]}
    clips=[]
    for i in range(1,PARTS+1):
        title0,typ,extra=SHOTS[(i-1)%len(SHOTS)]
        scene,png,commands=scene_for(i,title0,typ,extra)
        clip=render_part(i,scene,png)
        q=qc(clip)
        if not (q["video"] and 29.0<=q["duration"]<=31.0 and q["width"]==W and q["height"]==H):
            raise RuntimeError(f"PART_QC_FAILED:{i}:{q}")
        clips.append(clip)
        manifest["parts_manifest"].append({"part":i,"title":title0,"scene":scene,
                                            "machine_instruction_count":len(commands),"video":str(clip),"qc":q})
        (OUT/"manifest.partial.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    concat=OUT/"concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf-8")
    final=OUT/"final.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(final)],1800)
    final_qc=qc(final)
    if not (final_qc["video"] and 1790<=final_qc["duration"]<=1810 and final_qc["width"]==W and final_qc["height"]==H):
        raise RuntimeError(f"MASTER_QC_FAILED:{final_qc}")
    manifest["status"]="VERIFIED_COMPLETED"; manifest["final"]=str(final); manifest["master_qc"]=final_qc
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"VERIFIED_COMPLETED").write_text("BRAIN MACHINE CINEMA VERIFIED\n",encoding="utf-8")
    return manifest

if __name__=="__main__":
    print(json.dumps(build_film(os.environ.get("BRAIN_FILM_TITLE","BRAIN — فيلم الآلة")),ensure_ascii=False,indent=2))
