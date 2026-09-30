"""BRAIN Visual Engine: deterministic local text-to-scene compiler.

The engine is intentionally provider-free: text -> Scene JSON -> SVG/HTML.
No external image API is required. The scene contract is also suitable for
feeding BRAIN Media Engine timelines.
"""
import html
import re

MODES={"landscape","city","robot","car","abstract","green_mask"}

PALETTES={
    "default":{"sky":"#8ed8ff","sun":"#ffd84d","ground":"#6ca85a","dark":"#263746"},
    "night":{"sky":"#101827","sun":"#f3c969","ground":"#263746","dark":"#121b2a"},
    "sunset":{"sky":"#d97a6d","sun":"#ffd08a","ground":"#5f8057","dark":"#352d43"},
}

def _text(s):
    return (s or "").strip()

def _low(s):
    return _text(s).lower()

def _has(t,*words):
    return any(w in t for w in words)

def detect_mode(text:str, mode:str="auto")->str:
    if mode in MODES:
        return mode
    t=_low(text)
    if re.search(r"روبوت|robot|android",t): return "robot"
    if re.search(r"سيارة|car|automobile|vehicle",t): return "car"
    if re.search(r"مدينة|city|مبنى|مباني|building|street",t): return "city"
    if re.search(r"قناع أخضر|القناع الأخضر|green mask|mask",t): return "green_mask"
    if re.search(r"دائرة|مربع|مثلث|هندسي|abstract|geometric",t): return "abstract"
    return "landscape"

def detect_palette(text:str)->str:
    t=_low(text)
    if _has(t,"ليل","ليلي","night","dark"): return "night"
    if _has(t,"غروب","شروق","sunset","sunrise"): return "sunset"
    return "default"

def _objects(text:str, selected:str):
    t=_low(text)
    if selected=="green_mask":
        out=["sky","street","hero","mask","magic","buildings"]
        if _has(t,"مطر","rain"): out.append("rain")
        if _has(t,"ليل","ليلي","night"): out.append("night")
        if _has(t,"نادي","club","nightclub"): out.append("club")
        if _has(t,"سطح","rooftop","roof"): out.append("rooftop")
        return out
    if selected=="landscape":
        out=["sky","sun","mountains","ground"]
        if _has(t,"شجرة","شجر","tree","forest"): out.append("tree")
        if _has(t,"بحيرة","ماء","lake","water","river"): out.append("lake")
        if _has(t,"بيت","منزل","house","cabin"): out.append("house")
        if _has(t,"قمر","moon"): out.append("moon")
        if _has(t,"نجوم","نجمة","stars","star"): out.append("stars")
        return list(dict.fromkeys(out))
    if selected=="city":
        out=["sky","sun","buildings","road","car"]
        if _has(t,"برج","tower","skyscraper"): out.append("tower")
        if _has(t,"شجرة","tree"): out.append("tree")
        return out
    if selected=="robot":
        out=["background","ground","robot"]
        if _has(t,"مدينة","city"): out.append("city-lights")
        if _has(t,"قمر","moon"): out.append("moon")
        return out
    if selected=="car":
        out=["sky","ground","car"]
        if _has(t,"طريق","road","highway"): out.append("road")
        if _has(t,"شجرة","tree"): out.append("tree")
        return out
    return ["background","circle","triangle","square"]

def compile_scene(text:str, mode:str="auto")->dict:
    text=_text(text) or "منظر طبيعي"
    selected=detect_mode(text,mode)
    palette=detect_palette(text)
    objects=_objects(text,selected)
    return {
        "version":"1.1",
        "type":selected,
        "text":text,
        "objects":objects,
        "palette":palette,
        "renderer":"svg",
        "local":True,
        "external_api":False,
        "animation":{"enabled":False,"duration":5,"fps":30},
        "media":{"width":1000,"height":650,"fps":30},
    }

def scene_timeline(scene:dict,duration:float=5.0)->dict:
    d=max(0.5,float(duration))
    return {
        "version":"1.0",
        "profile":"youtube_1080p",
        "scenes":[{
            "id":"visual-scene-1",
            "duration":d,
            "asset_type":"svg",
            "scene":scene,
            "transition":"fade",
            "transition_duration":0.5,
        }],
        "metadata":{"source":"BRAIN Visual Engine","local":True}
    }

def render_svg(scene:dict)->str:
    text=html.escape(str(scene.get("text","")),quote=True)
    typ=scene.get("type","landscape")
    objects=scene.get("objects",[])
    palette=PALETTES.get(scene.get("palette","default"),PALETTES["default"])
    body=""
    if typ=="landscape":
        body=f'<rect width="1000" height="650" fill="{palette["sky"]}"/>'
        if "sun" in objects: body+=f'<circle cx="800" cy="115" r="65" fill="{palette["sun"]}"/>'
        if "moon" in objects: body+='<circle cx="800" cy="115" r="58" fill="#e8edf5"/><circle cx="820" cy="95" r="58" fill="'+palette["sky"]+'"/>'
        if "stars" in objects:
            body+=''.join(f'<circle cx="{x}" cy="{y}" r="4" fill="#fff"/>' for x,y in [(90,90),(180,145),(300,80),(420,130),(560,75),(690,150)])
        body+='<path d="M0 470L220 190 430 470 630 170 1000 470Z" fill="#667f92"/>'
        body+='<path d="M0 500L300 280 540 500 730 250 1000 500V650H0Z" fill="#435c70"/>'
        body+=f'<rect y="500" width="1000" height="150" fill="{palette["ground"]}"/>'
        if "lake" in objects: body+='<path d="M360 540 Q500 500 650 540 T930 540V650H360Z" fill="#4fa7c9"/>'
        if "tree" in objects: body+='<rect x="145" y="415" width="25" height="150" fill="#6b4226"/><path d="M158 300L80 450H236Z M158 350L95 485H220Z" fill="#285b32"/>'
        if "house" in objects: body+='<rect x="720" y="400" width="170" height="130" fill="#d98b5b"/><path d="M690 405L805 315 920 405Z" fill="#7d3d35"/><rect x="780" y="455" width="40" height="75" fill="#523d32"/>'
    elif typ=="city":
        body=f'<rect width="1000" height="650" fill="{palette["sky"]}"/><circle cx="820" cy="110" r="55" fill="{palette["sun"]}"/>'
        for i,x in enumerate([80,210,350,500,670,820]):
            y=250-(i%3)*45; h=400-(i%3)*45
            body+=f'<rect x="{x}" y="{y}" width="110" height="{h}" fill="#{["526b82","3f566b","657c91"][i%3]}"/>'
        if "tower" in objects: body+='<rect x="455" y="110" width="95" height="260" fill="#71889d"/><path d="M455 110L502 45 550 110Z" fill="#51697d"/>'
        body+='<path d="M0 650L350 490H650L1000 650Z" fill="#303c48"/><path d="M500 650L500 520" stroke="#f5d76e" stroke-width="12" stroke-dasharray="30 25"/>'
    elif typ=="green_mask":
        night = "night" in objects
        sky = "#07101f" if night else "#243f62"
        body=f'<rect width="1000" height="650" fill="{sky}"/>'
        body+='<circle cx="835" cy="105" r="48" fill="#d8e7f2" opacity=".9"/>'
        body+='<path d="M0 650L300 470H700L1000 650Z" fill="#111822"/>'
        body+='<rect x="120" y="250" width="150" height="220" fill="#182b3d"/><rect x="310" y="190" width="180" height="280" fill="#20374b"/><rect x="720" y="220" width="130" height="250" fill="#16293b"/>'
        for x in [145,190,335,390,435,750,795]:
            body+=f'<rect x="{x}" y="280" width="16" height="24" rx="3" fill="#f6d36a"/>'
        body+='<circle cx="500" cy="295" r="72" fill="#55d63f" opacity=".24"/>'
        body+='<path d="M452 445L470 330Q500 305 530 330L548 445Z" fill="#171b22"/><circle cx="500" cy="280" r="38" fill="#d7a37c"/>'
        body+='<path d="M455 260Q500 205 545 260L536 315Q500 335 464 315Z" fill="#15191e"/>'
        body+='<path d="M462 270Q500 235 538 270L532 304Q500 320 468 304Z" fill="#42d93c"/>'
        body+='<ellipse cx="500" cy="285" rx="42" ry="17" fill="#0c1b13"/><circle cx="480" cy="285" r="7" fill="#d9ff5b"/><circle cx="520" cy="285" r="7" fill="#d9ff5b"/>'
        body+='<path d="M430 370Q500 415 570 370" stroke="#51ff43" stroke-width="8" fill="none" opacity=".75"/>'
        if "rain" in objects:
            body+=''.join(f'<path d="M{x} {80+(x%5)*35}l-18 55" stroke="#8dd8ff" stroke-width="3" opacity=".55"/>' for x in range(40,980,55))
        if "magic" in objects:
            body+=''.join(f'<circle cx="{x}" cy="{y}" r="5" fill="#6cff4f" opacity=".8"/>' for x,y in [(380,220),(620,180),(680,340),(350,400),(650,440)])
        if "club" in objects:
            body+='<rect x="730" y="205" width="110" height="18" fill="#e44cff"/><circle cx="785" cy="205" r="35" fill="#e44cff" opacity=".18"/>'
    elif typ=="robot":
        body=f'<rect width="1000" height="650" fill="{palette["sky"]}"/><rect y="500" width="1000" height="150" fill="{palette["dark"]}"/>'
        body+='<rect x="360" y="220" width="280" height="220" rx="35" fill="#9aaabd"/><circle cx="440" cy="315" r="30" fill="#55d9ff"/><circle cx="560" cy="315" r="30" fill="#55d9ff"/><rect x="440" y="375" width="120" height="22" rx="11" fill="#243648"/><path d="M500 220V145" stroke="#9aaabd" stroke-width="14"/><circle cx="500" cy="125" r="22" fill="#ffd84d"/><rect x="300" y="260" width="60" height="150" rx="20" fill="#8799ad"/><rect x="640" y="260" width="60" height="150" rx="20" fill="#8799ad"/>'
        if "city-lights" in objects: body+=''.join(f'<circle cx="{x}" cy="480" r="6" fill="#ffd84d"/>' for x in range(80,940,70))
        if "moon" in objects: body+='<circle cx="820" cy="120" r="52" fill="#eef2f7"/>'
    elif typ=="car":
        body=f'<rect width="1000" height="650" fill="{palette["sky"]}"/><rect y="480" width="1000" height="170" fill="#343f49"/>'
        body+='<path d="M210 455L300 360H650L790 455Z" fill="#d84d4d"/><rect x="335" y="370" width="130" height="70" fill="#9bd9ee"/><rect x="480" y="370" width="135" height="70" fill="#9bd9ee"/><rect x="170" y="440" width="660" height="95" rx="35" fill="#d84d4d"/><circle cx="300" cy="535" r="58" fill="#171d22"/><circle cx="700" cy="535" r="58" fill="#171d22"/><circle cx="300" cy="535" r="25" fill="#aab5bd"/><circle cx="700" cy="535" r="25" fill="#aab5bd"/>'
        if "tree" in objects: body+='<rect x="90" y="390" width="20" height="120" fill="#6b4226"/><circle cx="100" cy="350" r="65" fill="#2f713d"/>'
    else:
        body='<rect width="1000" height="650" fill="#101827"/><circle cx="250" cy="300" r="120" fill="#ffcf4a"/><path d="M500 150L650 430H350Z" fill="#55c7a5"/><rect x="700" y="210" width="170" height="170" rx="25" fill="#d85b74"/>'
    title=f'<title>BRAIN Visual Engine: {text}</title>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 650" role="img">{title}{body}</svg>'
