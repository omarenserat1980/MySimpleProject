from __future__ import annotations
import argparse,math,subprocess,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
FILMS={
"room-13":{"title":"الغرفة 13","genre":"رعب • غموض","tone":1,"seconds":60},
"last-signal":{"title":"بعد الإشارة","genre":"خيال علمي • تشويق","tone":2,"seconds":60},
"zero-line":{"title":"خط الصفر","genre":"إثارة • مغامرة","tone":3,"seconds":60},
}
W,H=1280,720
def font(n):
 p="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
 return ImageFont.truetype(p,n) if Path(p).exists() else ImageFont.load_default()
def scene_image(spec,i,total):
 p=i/max(1,total-1);img=Image.new("RGB",(W,H));d=ImageDraw.Draw(img)
 tone=spec["tone"]
 if tone==1: base=(15+int(35*p),10+int(12*p),25+int(28*p)); accent=(210,90,110)
 elif tone==2: base=(7+int(12*p),20+int(35*p),35+int(60*p)); accent=(80,200,235)
 else: base=(35+int(30*p),18+int(30*p),8+int(12*p)); accent=(235,180,70)
 for y in range(H):
  q=y/H;d.line((0,y,W,y),fill=tuple(int(v*(1-q*.35)) for v in base))
 # evolving environment: corridor / signal / road
 if tone==1:
  for x in range(80,W,180):
   h=250+int(100*math.sin(x*.03+p*8));d.rectangle((x,H-h,x+90,H),fill=(8,8,14))
  d.ellipse((W*.68,H*.28,W*.68+110,H*.28+110),fill=accent)
 elif tone==2:
  cx=W*(.5+.35*math.sin(p*math.pi*2));cy=H*.45
  for r in range(40,300,45): d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=accent,width=3)
  d.polygon([(0,H),(W*.42,H*.55),(W*.58,H*.55),(W,H)],fill=(8,12,22))
 else:
  d.polygon([(W*.25,H),(W*.46,H*.48),(W*.54,H*.48),(W*.78,H)],fill=(18,16,12))
  d.line((W*.5,H*.48,W*.5,H),fill=accent,width=8)
 d.text((40,42),spec["title"],font=font(40),fill="white")
 d.text((40,92),spec["genre"],font=font(20),fill=accent)
 d.text((W-60,H-40),f"{i+1:05d}",font=font(18),fill="white",anchor="mm")
 return img
def render(spec,out,fps=12):
 out.mkdir(parents=True,exist_ok=True);frames=out/"frames";frames.mkdir(exist_ok=True)
 total=spec["seconds"]*fps
 for i in range(total):scene_image(spec,i,total).save(frames/f"f{i:06d}.png")
 ff=shutil.which("ffmpeg")
 if not ff:raise RuntimeError("FFMPEG_RUNTIME_REQUIRED")
 silent=out/"silent.mp4";master=out/"master.mp4"
 subprocess.run([ff,"-y","-loglevel","error","-framerate",str(fps),"-i",str(frames/"f%06d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(silent)],check=True)
 subprocess.run([ff,"-y","-loglevel","error","-i",str(silent),"-f","lavfi","-i",f"sine=frequency={180+spec['tone']*80}:duration={spec['seconds']}","-c:v","copy","-c:a","aac","-shortest","-movflags","+faststart",str(master)],check=True)
 return master
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("film",choices=FILMS);ap.add_argument("--out",default="/tmp/brain-films");a=ap.parse_args()
 print(render(FILMS[a.film],Path(a.out)/a.film))
