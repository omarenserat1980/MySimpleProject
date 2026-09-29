#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, subprocess, shutil
ROOT=pathlib.Path(__file__).resolve().parents[2]
PLAN=ROOT/"brain_v12/movie_summary_factory/jobs/room-13-horror-10m-cinematic-v3.json"
OUT=ROOT/"brain_v12/web/media/engine/room-13-horror-10m-animatic.mp4"
FONT="/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
if not pathlib.Path(FONT).exists(): FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
plan=json.loads(PLAN.read_text(encoding="utf-8")); shots=plan["shots"]; target=plan["target_minutes"]*60
per=target/len(shots)
ff=shutil.which("ffmpeg")
if not ff: raise SystemExit("FFMPEG_NOT_INSTALLED")
OUT.parent.mkdir(parents=True,exist_ok=True)
segments=[]
def esc(t): return str(t).replace("\\","\\\\").replace(":","\\:").replace("'","\\'").replace("%","\\%").replace(",","\\,")
for i,s in enumerate(shots):
 d=per; progress=int(((i+1)/len(shots))*100); label=esc(f'{s["id"]} — {s["visual"]}')
 vf=f"scale=1920:1080,format=yuv420p,drawtext=fontfile='{FONT}':text='{label}':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=42:fontcolor=white:borderw=3:bordercolor=black,fade=t=in:st=0:d=1,fade=t=out:st={max(0,d-1)}:d=1"
 out=OUT.parent/f"room13-segment-{i:02d}.mp4"
 subprocess.run([ff,"-y","-hide_banner","-loglevel","error","-f","lavfi","-i","color=c=black:s=1920x1080:r=24","-t",f"{d:.3f}","-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p",str(out)],check=True)
 segments.append(out)
 print(f"ROOM_13_PROGRESS={progress}% shot={i+1}/{len(shots)}", flush=True)
lst=OUT.parent/"room13-concat.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments),encoding="utf-8")
subprocess.run([ff,"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(lst),"-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart","-an",str(OUT)],check=True)
for p in segments: p.unlink(missing_ok=True)
lst.unlink(missing_ok=True)
progress_path=OUT.parent/"room-13-progress.json"
progress_path.write_text(json.dumps({"status":"RENDERED","percent":100,"duration_seconds":target,"shots":len(shots),"output":str(OUT)},ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"status":"RENDERED","percent":100,"output":str(OUT),"duration_seconds":target,"shots":len(shots)},ensure_ascii=False))
