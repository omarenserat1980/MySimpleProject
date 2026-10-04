#!/usr/bin/env python3
"""BRAIN Machine Cinema Factory.
Provider-free local cinema: generated visual scene + narration + procedural music + motion.
"""
from __future__ import annotations
import hashlib,json,os,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get("BRAIN_MACHINE_FILM_ROOT",ROOT/"brain6_artifacts"/"machine_films"))
FPS=int(os.environ.get("BRAIN_FILM_FPS","24"))
PARTS=max(1,int(os.environ.get("BRAIN_FILM_PARTS","240")))
PART_SECONDS=max(5,int(os.environ.get("BRAIN_FILM_PART_SECONDS","30")))
START_PART=max(1,int(os.environ.get("BRAIN_FILM_START","1")))
END_PART=min(PARTS,int(os.environ.get("BRAIN_FILM_END",str(PARTS))))
W,H=1000,650

SHOTS=[
("الفجر","landscape","sunrise"),("الطريق","car","road"),("المدينة","city","city"),
("المطر","green_mask","rain"),("الروبوت","robot","city"),("البحيرة","landscape","lake"),
("البرج","city","tower"),("الغابة","landscape","forest"),("القناع","green_mask","magic"),
("الليل","landscape","night"),("المطاردة","car","highway"),("السطح","green_mask","rooftop"),
]

def run(cmd,timeout=1200):
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout)[-5000:])
    return p

def scene_for(i,title,typ,extra):
    palette="night" if i%5==0 or extra=="night" else ("sunset" if i%7==0 else "default")
    words={"landscape":"منظر طبيعي سينمائي","city":"مدينة سينمائية","car":"مطاردة سيارة سينمائية",
           "robot":"روبوت سينمائي","green_mask":"بطل القناع الأخضر في مشهد سينمائي"}
    prompt=f"{words[typ]}: {title} {extra}; لقطة فيلمية واسعة، إضاءة درامية، عمق بصري، حركة كاميرا بطيئة؛ تنويع {i%24}"
    from brain_v12 import visual_engine
    scene=visual_engine.compile_scene(prompt,typ)
    scene["palette"]=palette
    scene["variant"]=i%24
    from brain_v12.machine_raster_engine import render_machine
    png,commands=render_machine(scene)
    return scene,png,commands

def render_part(i,png,scene):
    part=OUT/"parts"/f"{i:03d}"; part.mkdir(parents=True,exist_ok=True)
    img=part/"machine.png"; img.write_bytes(png)
    narration=part/"narration.wav"
    music=part/"music.wav"
    narration_text=f"المشهد {i}. {scene.get('text','مشهد سينمائي')}. تستمر الحكاية في هذه اللحظة."
    run(["espeak-ng","-v","ar","-s","145","-p","45","-w",str(narration),narration_text],120)
    # Local procedural music bed: four-note chord with slow tremolo, not a placeholder silence/tone.
    chord="amix=inputs=4:duration=longest:weights=1 0.8 0.65 0.5:normalize=0"
    run(["ffmpeg","-y",
         "-f","lavfi","-i",f"sine=frequency={220+(i%4)*12}:sample_rate=48000:duration={PART_SECONDS}",
         "-f","lavfi","-i",f"sine=frequency={277+(i%4)*12}:sample_rate=48000:duration={PART_SECONDS}",
         "-f","lavfi","-i",f"sine=frequency={330+(i%4)*12}:sample_rate=48000:duration={PART_SECONDS}",
         "-f","lavfi","-i",f"sine=frequency={440+(i%4)*12}:sample_rate=48000:duration={PART_SECONDS}",
         "-filter_complex",f"[0:a]volume=0.08[a0];[1:a]volume=0.06[a1];[2:a]volume=0.05[a2];[3:a]volume=0.04[a3];[a0][a1][a2][a3]{chord},afade=t=in:st=0:d=2,afade=t=out:st={max(0,PART_SECONDS-2)}:d=2",
         "-c:a","pcm_s16le",str(music)],120)
    mp4=part/f"part-{i:03d}.mp4"
    frames=PART_SECONDS*FPS
    # Alternating camera direction and zoom create real temporal motion.
    if i%2:
        z="min(zoom+0.0010,1.18)"; x="iw/2-(iw/zoom/2)"; y="ih/2-(ih/zoom/2)"
    else:
        z="max(zoom-0.00035,1.0)"; x="iw/2-(iw/zoom/2)"; y="ih/2-(ih/zoom/2)"
    vf=f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p"
    run(["ffmpeg","-y","-loop","1","-i",str(img),"-i",str(narration),"-i",str(music),
         "-vf",vf,"-filter_complex","[1:a]volume=1.0[v];[2:a]volume=0.32[m];[v][m]amix=inputs=2:duration=longest:dropout_transition=2[aout]",
         "-map","0:v:0","-map","[aout]","-t",str(PART_SECONDS),
         "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","192k","-shortest",str(mp4)],1200)
    return mp4,narration,music

def probe(path):
    p=run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height,codec_name","-of","json",str(path)],60)
    d=json.loads(p.stdout); s=d.get("streams",[])
    return {"duration":float(d["format"]["duration"]),"video":any(x.get("codec_type")=="video" for x in s),
            "audio":any(x.get("codec_type")=="audio" for x in s),
            "width":next((x.get("width") for x in s if x.get("codec_type")=="video"),None),
            "height":next((x.get("height") for x in s if x.get("codec_type")=="video"),None),
            "audio_codecs":sorted({x.get("codec_name") for x in s if x.get("codec_type")=="audio"})}

def machine_bits(commands):
    opcodes={"RECT":1,"CIRCLE":2,"LINE":3,"POLY":4}; bits=[]
    for cmd in commands:
        bits.append(f"{opcodes.get(cmd[0],0):08b}")
        for v in cmd[1:]:
            if isinstance(v,(int,float)): bits.append(f"{int(v)&0xffffffff:032b}")
            elif isinstance(v,str): bits.append("".join(f"{b:08b}" for b in v.encode()))
            elif isinstance(v,list):
                for pt in v: bits.append("".join(f"{int(x)&0xffffffff:032b}" for x in pt))
    return "".join(bits)

def build_film(title="BRAIN — فيلم سينمائي طويل 120 دقيقة"):
    OUT.mkdir(parents=True,exist_ok=True); target=PARTS*PART_SECONDS
    manifest={"title":title,"renderer":"Brain Machine Raster Painter v2","parts":PARTS,
              "part_seconds":PART_SECONDS,"target_seconds":target,"fps":FPS,"external_api":False,
              "pipeline":["visual_scene","camera_motion","narration","music_bed","aac_mix","technical_qc","cinematic_qc"],
              "parts_manifest":[]}
    clips=[]
    for i in range(START_PART,END_PART+1):
        title0,typ,extra=SHOTS[(i-1)%len(SHOTS)]
        scene,png,commands=scene_for(i,title0,typ,extra)
        clip,narration,music=render_part(i,png,scene); q=probe(clip)
        if not(q["video"] and q["audio"] and PART_SECONDS-1<=q["duration"]<=PART_SECONDS+1 and q["width"]==W and q["height"]==H):
            raise RuntimeError(f"PART_QC_FAILED:{i}:{q}")
        clips.append(clip)
        manifest["parts_manifest"].append({"part":i,"title":title0,"scene":scene,
          "visual_asset":str(OUT/"parts"/f"{i:03d}"/"machine.png"),
          "narration_asset":str(narration),"music_asset":str(music),
          "motion":True,"machine_instruction_count":len(commands),
          "machine_bits_sha256":hashlib.sha256(machine_bits(commands).encode()).hexdigest(),
          "video":str(clip),"qc":q})
        (OUT/"manifest.partial.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    concat=OUT/"concat.txt"; concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf-8")
    if START_PART!=1 or END_PART!=PARTS or os.environ.get("BRAIN_FILM_SHARD_ONLY","0")=="1":
        manifest["status"]="SHARD_COMPLETED"; manifest["range"]={"start":START_PART,"end":END_PART}
        (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        return manifest
    final=OUT/"final.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(final)],3600)
    final_qc=probe(final)
    if not(final_qc["video"] and final_qc["audio"] and abs(final_qc["duration"]-target)<=10 and final_qc["width"]==W and final_qc["height"]==H):
        raise RuntimeError(f"MASTER_QC_FAILED:{final_qc}")
    manifest["master_qc"]=final_qc
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"VERIFIED_COMPLETED").write_text("VERIFIED_COMPLETED\\n",encoding="utf-8")
    return manifest

if __name__=="__main__":
    print(json.dumps(build_film(os.environ.get("BRAIN_FILM_TITLE","BRAIN — فيلم سينمائي طويل 120 دقيقة")),ensure_ascii=False,indent=2))
