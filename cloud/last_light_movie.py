"""Local no-pay cinematic renderer for «آخر ضوء في المدينة»."""
from __future__ import annotations
import argparse, math, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720

def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def frame(i, total):
    p = i / max(1, total - 1)
    img = Image.new("RGB", (W, H), (14, 18, 30))
    d = ImageDraw.Draw(img)
    # dawn/night gradient
    for y in range(H):
        t = y / H
        r = int(16 + 90 * p + 20 * t)
        g = int(20 + 55 * p + 18 * t)
        b = int(38 + 40 * p + 12 * t)
        d.line((0, y, W, y), fill=(r, g, b))
    # sun / last light
    sx = int(W * (0.12 + 0.76 * p))
    sy = int(H * (0.63 - 0.25 * math.sin(math.pi * p)))
    radius = int(55 + 35 * math.sin(math.pi * p))
    d.ellipse((sx-radius, sy-radius, sx+radius, sy+radius), fill=(245, 205, 115))
    # city silhouette
    buildings = [(0,520,150,720),(125,455,270,720),(245,500,360,720),(340,420,500,720),
                 (480,475,610,720),(590,390,735,720),(720,450,870,720),(850,410,1010,720),
                 (990,485,1130,720),(1110,440,1280,720)]
    for x1,y1,x2,y2 in buildings:
        d.rectangle((x1,y1,x2,y2), fill=(20,22,28))
        for wx in range(x1+18, x2-8, 30):
            for wy in range(y1+25, y2-10, 42):
                if (wx//30 + wy//42 + i//8) % 5 == 0:
                    d.rectangle((wx,wy,wx+9,wy+14), fill=(205,175,100))
    # flipbook paper border / frame marker
    d.rectangle((28,28,W-28,H-28), outline=(220,220,220), width=2)
    title = "آخر ضوء في المدينة"
    d.text((W//2, 70), title, anchor="mm", font=font(42), fill=(245,245,245))
    d.text((W-70,H-45), f"{i+1:04d}", anchor="mm", font=font(22), fill=(210,210,210))
    return img

def render(out: Path, seconds=12, fps=12):
    out.mkdir(parents=True, exist_ok=True)
    frames = out / "frames"
    frames.mkdir(exist_ok=True)
    total = seconds * fps
    for i in range(total):
        frame(i, total).save(frames / f"frame_{i+1:05d}.png")
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    silent = out / "silent.mp4"
    final = out / "last_light_city.mp4"
    subprocess.run([ffmpeg,"-y","-loglevel","error","-framerate",str(fps),
                    "-i",str(frames/"frame_%05d.png"),"-c:v","libx264","-pix_fmt","yuv420p",
                    "-movflags","+faststart",str(silent)], check=True)
    subprocess.run([ffmpeg,"-y","-loglevel","error","-i",str(silent),
                    "-f","lavfi","-i",f"sine=frequency=220:duration={seconds}",
                    "-c:v","copy","-c:a","aac","-shortest","-movflags","+faststart",str(final)], check=True)
    silent.unlink(missing_ok=True)
    return final

if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="/tmp/last-light")
    ap.add_argument("--seconds",type=int,default=12)
    ap.add_argument("--fps",type=int,default=12)
    a=ap.parse_args()
    p=render(Path(a.output), max(1,a.seconds), max(1,a.fps))
    print(p)
