"""Digital flipbook renderer."""
from __future__ import annotations
import argparse, json, math, os, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

def draw_frame(size, index, total):
    width, height = size
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((32,32,width-32,height-32), outline=(215,215,215), width=2)
    for y in range(72,height-40,32):
        draw.line((48,y,width-48,y), fill=(238,238,238), width=1)
    draw.line((88,48,88,height-48), fill=(235,205,205), width=2)
    p = 0.0 if total <= 1 else index/(total-1)
    x = width*(0.18+0.64*p)
    arc = math.sin(math.pi*p)
    y = height*(0.72-0.42*arc)
    r = max(18,min(width,height)//18)
    shadow_scale = 0.55+0.45*(1.0-arc)
    sx, sy = int(x), int(height*0.76)
    draw.ellipse((sx-int(r*shadow_scale),sy-8,sx+int(r*shadow_scale),sy+8),fill=(225,225,225))
    draw.ellipse((int(x-r),int(y-r),int(x+r),int(y+r)),outline=(25,25,25),width=5)
    draw.ellipse((int(x-r*0.45),int(y-r*0.55),int(x-r*0.05),int(y-r*0.15)),fill=(245,245,245))
    draw.text((width-190,height-74),f"FRAME {index+1:04d}",fill=(70,70,70))
    return image

def render_frames(output_dir, frames=24, width=640, height=360):
    if frames < 2: raise ValueError("frames must be >= 2")
    root=Path(output_dir); root.mkdir(parents=True,exist_ok=True)
    paths=[]
    for i in range(frames):
        path=root/f"frame_{i+1:04d}.png"
        draw_frame((width,height),i,frames).save(path,"PNG")
        paths.append(path)
    return paths

def render_video(frame_dir, output_file, fps=12):
    if fps <= 0: raise ValueError("fps must be positive")
    ffmpeg=os.environ.get("BRAIN_FFMPEG_BIN",shutil.which("ffmpeg") or "ffmpeg")
    output=Path(output_file); output.parent.mkdir(parents=True,exist_ok=True)
    cmd=[ffmpeg,"-y","-loglevel","error","-framerate",str(fps),"-i",str(Path(frame_dir)/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(output)]
    subprocess.run(cmd,check=True)
    return output

def build_flipbook(work_dir, frames=24, fps=12):
    root=Path(work_dir); frame_dir=root/"frames"; video=root/"flipbook.mp4"
    paths=render_frames(frame_dir,frames=frames); render_video(frame_dir,video,fps=fps)
    return {"format":"digital_flipbook","frames":len(paths),"fps":fps,"frame_pattern":"frames/frame_%04d.png","video":str(video),"verified":video.exists() and video.stat().st_size>0}

def main():
    parser=argparse.ArgumentParser(description="Render a deterministic digital flipbook.")
    parser.add_argument("--output",default="/tmp/brain-flipbook"); parser.add_argument("--frames",type=int,default=24); parser.add_argument("--fps",type=int,default=12)
    args=parser.parse_args(); print(json.dumps(build_flipbook(args.output,args.frames,args.fps),ensure_ascii=False,indent=2))

if __name__=="__main__": main()
