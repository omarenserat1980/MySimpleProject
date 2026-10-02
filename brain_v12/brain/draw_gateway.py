"""Human-to-image routing for BRAIN. Local mode produces verified SVG plus raster PNG."""
from __future__ import annotations
import base64, re
from pathlib import Path
from typing import Any, Callable
from .. import visual_engine
from .. import machine_raster_engine

_DRAW_WORDS=("ارسم","ارسم لي","صورة","draw","image","picture")
_CHATGPT_WORDS=("chatgpt","شات جي بي تي","شاتجبت","openai")

def parse_human_draw_request(message:str)->dict[str,Any]:
    text=(message or "").strip(); low=text.lower()
    is_draw=any(w in low for w in _DRAW_WORDS)
    wants_chatgpt=any(w in low for w in _CHATGPT_WORDS)
    prompt=re.sub(r"(?i)^.*?(?:ارسم(?:\s+لي)?|draw|create an image of|generate an image of)\s*","",text).strip() or text
    return {"ok":bool(is_draw),"intent":"DRAW_IMAGE" if is_draw else "CHAT",
            "provider":"openai" if wants_chatgpt else "local","prompt":prompt or "منظر طبيعي"}

def draw_local(prompt:str, mode:str="auto")->dict[str,Any]:
    scene=visual_engine.compile_scene(prompt,mode)
    png,commands=machine_raster_engine.render_machine(scene)
    valid=png.startswith(b"\x89PNG\r\n\x1a\n") and len(png)>128
    svg=visual_engine.render_svg(scene)
    valid_svg=svg.lstrip().startswith("<svg") and "</svg>" in svg
    verified=valid and valid_svg
    return {"ok":verified,"provider":"brain_local_machine_raster","verified":verified,
            "scene":scene,"svg":svg,"png_base64":base64.b64encode(png).decode("ascii"),
            "machine_commands":commands,"format":"svg","raster_format":"png","renderer":"machine-raster+svg-scene"}

def save_png_base64(data:str,target:Path)->int:
    raw=base64.b64decode(data,validate=True)
    if len(raw)<128: raise ValueError("IMAGE_TOO_SMALL")
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw); return len(raw)

def draw_openai(prompt:str,generator:Callable[[str],dict[str,Any]],media_root:Path)->dict[str,Any]:
    result=generator(prompt)
    if not result.get("ok"): return result
    data=result.get("b64_json") or result.get("image_base64")
    if not data: return {"ok":False,"error":"OPENAI_IMAGE_DATA_MISSING"}
    filename="brain-openai-draw-"+__import__("uuid").uuid4().hex+".png"
    size=save_png_base64(data,media_root/filename)
    return {"ok":True,"provider":"openai","verified":size>=128,"filename":filename,"url":"/media/"+filename,"bytes":size,"format":"png","model":result.get("model")}
