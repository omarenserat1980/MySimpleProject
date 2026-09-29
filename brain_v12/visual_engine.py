"""BRAIN Visual Engine: deterministic text-to-scene compiler with no external image API."""
import re

MODES={"landscape","city","robot","car","abstract"}

def detect_mode(text:str, mode:str="auto")->str:
    if mode in MODES:
        return mode
    t=text.lower()
    if re.search(r"روبوت|robot",t): return "robot"
    if re.search(r"سيارة|car|automobile",t): return "car"
    if re.search(r"مدينة|city|مبنى|building",t): return "city"
    if re.search(r"دائرة|مربع|مثلث|هندسي|abstract",t): return "abstract"
    return "landscape"

def compile_scene(text:str, mode:str="auto")->dict:
    text=(text or "منظر طبيعي").strip()
    selected=detect_mode(text,mode)
    low=text.lower()
    def has(*words): return any(w in low for w in words)
    objects=[]
    if selected=="landscape":
        objects=["sky","sun"]
        for words,name in [(("جبل","جبال","mountain"),"mountains"),(("شجرة","شجر","tree"),"tree"),(("بحيرة","ماء","lake","water"),"lake"),(("بيت","منزل","house"),"house")]:
            if has(*words): objects.append(name)
        if len(objects)==2: objects += ["mountains","tree","lake"]
    elif selected=="city": objects=["sky","sun","buildings","road","car"]
    elif selected=="robot": objects=["background","ground","robot"]
    elif selected=="car": objects=["sky","ground","car"]
    else: objects=["background","circle","triangle","square"]
    return {"type":selected,"text":text,"objects":objects,"renderer":"svg","local":True,"external_api":False}

def render_svg(scene:dict)->str:
    import html
    text=html.escape(scene["text"],quote=True)
    typ=scene["type"]; objects=scene["objects"]; body=""
    if typ=="landscape":
        body='<rect width="1000" height="650" fill="#8ed8ff"/><circle cx="800" cy="115" r="65" fill="#ffd84d"/>'
        if "mountains" in objects: body+='<path d="M0 470L220 190 430 470 630 170 1000 470Z" fill="#667f92"/><path d="M0 500L300 280 540 500 730 250 1000 500V650H0Z" fill="#435c70"/>'
        body+='<rect y="500" width="1000" height="150" fill="#6ca85a"/>'
        if "lake" in objects: body+='<path d="M360 540 Q500 500 650 540 T930 540V650H360Z" fill="#4fa7c9"/>'
        if "tree" in objects: body+='<rect x="145" y="415" width="25" height="150" fill="#6b4226"/><path d="M158 300L80 450H236Z M158 350L95 485H220Z" fill="#285b32"/>'
        if "house" in objects: body+='<rect x="720" y="400" width="170" height="130" fill="#d98b5b"/><path d="M690 405L805 315 920 405Z" fill="#7d3d35"/><rect x="780" y="455" width="40" height="75" fill="#523d32"/>'
    elif typ=="city":
        body='<rect width="1000" height="650" fill="#8bcfff"/><circle cx="820" cy="110" r="55" fill="#ffd84d"/>'
        for i,x in enumerate([80,210,350,500,670,820]): body+=f'<rect x="{x}" y="{250-(i%3)*45}" width="110" height="{400-(i%3)*45}" fill="{["#526b82","#3f566b","#657c91"][i%3]}"/>'
        body+='<path d="M0 650L350 490H650L1000 650Z" fill="#303c48"/><path d="M500 650L500 520" stroke="#f5d76e" stroke-width="12" stroke-dasharray="30 25"/>'
    elif typ=="robot":
        body='<rect width="1000" height="650" fill="#16243a"/><rect y="500" width="1000" height="150" fill="#263746"/><rect x="360" y="220" width="280" height="220" rx="35" fill="#9aaabd"/><circle cx="440" cy="315" r="30" fill="#55d9ff"/><circle cx="560" cy="315" r="30" fill="#55d9ff"/><rect x="440" y="375" width="120" height="22" rx="11" fill="#243648"/><path d="M500 220V145" stroke="#9aaabd" stroke-width="14"/><circle cx="500" cy="125" r="22" fill="#ffd84d"/>'
    elif typ=="car":
        body='<rect width="1000" height="650" fill="#91d7ff"/><rect y="480" width="1000" height="170" fill="#343f49"/><path d="M210 455L300 360H650L790 455Z" fill="#d84d4d"/><rect x="335" y="370" width="130" height="70" fill="#9bd9ee"/><rect x="480" y="370" width="135" height="70" fill="#9bd9ee"/><rect x="170" y="440" width="660" height="95" rx="35" fill="#d84d4d"/><circle cx="300" cy="535" r="58" fill="#171d22"/><circle cx="700" cy="535" r="58" fill="#171d22"/>'
    else:
        body='<rect width="1000" height="650" fill="#101827"/><circle cx="250" cy="300" r="120" fill="#ffcf4a"/><path d="M500 150L650 430H350Z" fill="#55c7a5"/><rect x="700" y="210" width="170" height="170" rx="25" fill="#d85b74"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 650" role="img"><title>BRAIN Visual Engine: {text}</title>{body}</svg>'
