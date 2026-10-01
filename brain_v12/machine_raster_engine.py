"""BRAIN Machine Raster Painter.

Pure-Python raster backend: Scene JSON -> low-level pixel drawing commands -> PNG.
No SVG, Pillow, browser, GPU, or external image API is required.
"""
from __future__ import annotations
import struct, zlib, hashlib
from typing import Iterable

W, H = 1000, 650

def _rgba(c):
    if isinstance(c, tuple): return c
    c = c.lstrip("#")
    if len(c) == 3: c = "".join(x+x for x in c)
    return tuple(int(c[i:i+2],16) for i in (0,2,4)) + (255,)

class PixelBuffer:
    def __init__(self,w=W,h=H,bg=(0,0,0,255)):
        self.w,self.h=w,h
        self.px=bytearray(_rgba(bg)*(w*h))
    def pixel(self,x,y,c):
        x,y=int(x),int(y)
        if 0<=x<self.w and 0<=y<self.h:
            i=(y*self.w+x)*4; self.px[i:i+4]=bytes(_rgba(c))
    def rect(self,x0,y0,x1,y1,c):
        x0,x1=sorted((int(x0),int(x1))); y0,y1=sorted((int(y0),int(y1)))
        for y in range(max(0,y0),min(self.h,y1+1)):
            a=(y*self.w+max(0,x0))*4; b=(y*self.w+min(self.w,x1+1))*4
            self.px[a:b]=bytes(_rgba(c))*((b-a)//4)
    def circle(self,cx,cy,r,c):
        r=int(r); rr=r*r
        for y in range(max(0,int(cy-r)),min(self.h,int(cy+r+1))):
            dy=y-cy
            for x in range(max(0,int(cx-r)),min(self.w,int(cx+r+1))):
                dx=x-cx
                if dx*dx+dy*dy<=rr: self.pixel(x,y,c)
    def line(self,x0,y0,x1,y1,c,width=1):
        dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
        while True:
            self.circle(x0,y0,max(0,int(width/2)),c)
            if x0==x1 and y0==y1: break
            e=2*err
            if e>=dy: err+=dy; x0+=sx
            if e<=dx: err+=dx; y0+=sy
    def polygon(self,points,c):
        ys=[p[1] for p in points]; y0=max(0,int(min(ys))); y1=min(self.h-1,int(max(ys)))
        for y in range(y0,y1+1):
            xs=[]
            for i,(x1,yy1) in enumerate(points):
                x2,yy2=points[(i+1)%len(points)]
                if (yy1<=y<yy2) or (yy2<=y<yy1):
                    xs.append(int(x1+(y-yy1)*(x2-x1)/(yy2-yy1)))
            xs.sort()
            for a,b in zip(xs[::2],xs[1::2]): self.rect(a,y,b,y,c)

def _chunk(kind,data):
    raw=struct.pack(">I",len(data))+kind+data
    import binascii
    return raw+struct.pack(">I",binascii.crc32(kind+data)&0xffffffff)

def png_bytes(buf:PixelBuffer):
    rows=[]
    for y in range(buf.h):
        rows.append(b"\x00"+bytes(buf.px[y*buf.w*4:(y+1)*buf.w*4]))
    raw=zlib.compress(b"".join(rows),9)
    return b"\x89PNG\r
\x1a
"+_chunk(b"IHDR",struct.pack(">IIBBBBB",buf.w,buf.h,8,6,0,0,0))+_chunk(b"IDAT",raw)+_chunk(b"IEND",b"")

def compile_machine_commands(scene:dict):
    typ=scene.get("type","landscape"); pal=scene.get("palette","default"); objects=scene.get("objects",[])
    seed_text=str(scene.get("scene_id", scene.get("title", "")))+"|"+str(scene.get("variant", 0))
    seed=int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:8],16)
    dx=(seed % 121)-60; dy=((seed >> 8) % 61)-30
    sun_r=45+((seed >> 16) % 31)
    sky={"default":"#8ed8ff","night":"#101827","sunset":"#d97a6d"}.get(pal,"#8ed8ff")
    ground={"default":"#6ca85a","night":"#263746","sunset":"#5f8057"}.get(pal,"#6ca85a")
    cmds=[("RECT",0,0,W,H,sky)]
    if typ=="landscape":
        cmds += [("POLY",[(0,470),(220,190),(430,470),(630,170),(1000,470)],"#667f92"),
                 ("POLY",[(0,500),(300,280),(540,500),(730,250),(1000,500),(1000,650),(0,650)],"#435c70"),
                 ("RECT",0,500,1000,650,ground)]
        if "sun" in objects: cmds.append(("CIRCLE",800+dx//3,115+dy//3,sun_r,"#ffd84d"))
        if "moon" in objects: cmds += [("CIRCLE",800+dx//3,115+dy//3,58,"#e8edf5"),("CIRCLE",820+dx//3,95+dy//3,58,sky)]
        if "stars" in objects:
            for n,(x,y) in enumerate([(90,90),(180,145),(300,80),(420,130),(560,75),(690,150),(760,65),(900,135)]):
                if n < 6 + seed % 3: cmds.append(("CIRCLE",(x+dx//4)%980+10,(y+dy//4)%180+30,3+(seed+n)%3,"#ffffff"))
        if "lake" in objects: cmds.append(("POLY",[(360,540),(500,500),(650,540),(930,540),(930,650),(360,650)],"#4fa7c9"))
        if "tree" in objects:
            cmds += [("RECT",145,415,170,565,"#6b4226"),("POLY",[(158,300),(80,450),(236,450)],"#285b32"),("POLY",[(158,350),(95,485),(220,485)],"#285b32")]
        if "house" in objects:
            cmds += [("RECT",720,400,890,530,"#d98b5b"),("POLY",[(690,405),(805,315),(920,405)],"#7d3d35"),("RECT",780,455,820,530,"#523d32")]
    elif typ=="city":
        cmds.append(("CIRCLE",820,110,55,"#ffd84d"))
        for i,x in enumerate([80,210,350,500,670,820]):
            y=250-(i%3)*45; h=400-(i%3)*45
            cmds.append(("RECT",x,y,x+110,y+h,["#526b82","#3f566b","#657c91"][i%3]))
        cmds += [("POLY",[(0,650),(350,490),(650,490),(1000,650)],"#303c48"),("LINE",500,650,500,520,"#f5d76e",12)]
    elif typ=="robot":
        cmds += [("RECT",0,500,1000,650,"#263746"),("RECT",360,220,640,440,"#9aaabd"),
                 ("CIRCLE",440,315,30,"#55d9ff"),("CIRCLE",560,315,30,"#55d9ff"),("RECT",440,375,560,397,"#243648"),
                 ("LINE",500,220,500,145,"#9aaabd",14),("CIRCLE",500,125,22,"#ffd84d")]
    elif typ=="car":
        cmds += [("RECT",0,480,1000,650,"#343f49"),("POLY",[(210,455),(300,360),(650,360),(790,455)],"#d84d4d"),
                 ("RECT",335,370,465,440,"#9bd9ee"),("RECT",480,370,615,440,"#9bd9ee"),("RECT",170,440,830,535,"#d84d4d"),
                 ("CIRCLE",300,535,58,"#171d22"),("CIRCLE",700,535,58,"#171d22")]
    elif typ=="green_mask":
        cmds += [("CIRCLE",835,105,48,"#d8e7f2"),("POLY",[(0,650),(300,470),(700,470),(1000,650)],"#111822"),
                 ("RECT",120,250,270,470,"#182b3d"),("RECT",310,190,490,470,"#20374b"),("RECT",720,220,850,470,"#16293b"),
                 ("CIRCLE",500,295,72,"#55d63f"),("CIRCLE",500,280,38,"#d7a37c"),("POLY",[(455,260),(500,205),(545,260),(536,315),(464,315)],"#15191e"),
                 ("POLY",[(462,270),(500,235),(538,270),(532,304),(468,304)],"#42d93c"),
                 ("CIRCLE",480,285,7,"#d9ff5b"),("CIRCLE",520,285,7,"#d9ff5b")]
        if "rain" in objects:
            for x in range(40,980,55): cmds.append(("LINE",x,80+(x%5)*35,x-18,135+(x%5)*35,"#8dd8ff",3))
    else:
        cmds += [("CIRCLE",250,300,120,"#ffcf4a"),("POLY",[(500,150),(650,430),(350,430)],"#55c7a5"),("RECT",700,210,870,380,"#d85b74")]
    return cmds

def render_machine(scene:dict):
    """Render a deterministic, materially varied raster scene."""
    buf=PixelBuffer()
    for cmd in compile_machine_commands(scene):
        op=cmd[0]
        if op=="RECT": buf.rect(*cmd[1:])
        elif op=="CIRCLE": buf.circle(*cmd[1:])
        elif op=="LINE": buf.line(*cmd[1:])
        elif op=="POLY": buf.polygon(*cmd[1:])
    return png_bytes(buf), compile_machine_commands(scene)
