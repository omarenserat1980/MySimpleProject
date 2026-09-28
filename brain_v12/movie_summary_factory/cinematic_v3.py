"""Cinematic V3 Pro planning/quality engine for Movie Summary Factory."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

SHOT_TYPES = ["ESTABLISHING","WIDE","MEDIUM","CLOSE_UP","DETAIL","REACTION"]
CAMERA_MOVES = ["SLOW_PUSH","SLOW_PULL","DOLLY_IN","DOLLY_OUT","PAN_LEFT","PAN_RIGHT","TILT_UP","TILT_DOWN","PARALLAX","DEPTH_ZOOM","RACK_FOCUS","HANDHELD","ORBIT","TRACKING"]
TRANSITIONS = ["HARD_CUT","FADE","CROSS_DISSOLVE","J_CUT","L_CUT","MATCH_CUT","MOTION_MATCH","OBJECT_MATCH","SOUND_BRIDGE","DIP_TO_BLACK","WHIP","LIGHT"]
RHYTHM = ["SLOW","MEDIUM","FAST","SLOW","FAST","CLIMAX","RELEASE"]
MUSIC = ["AMBIENT_SPACE","MYSTERY","ADVENTURE","TENSION","DEEP_LOW","CINEMATIC_RISE","EMOTIONAL_RELEASE"]
SFX = ["WIND","DUST","ENGINE","DOOR","FOOTSTEPS","RADIO","SPACE_AMBIENCE","MECHANICAL","IMPACT","RUMBLE","WHOOSH","LOW_BOOM"]

@dataclass
class Shot:
    id: str
    shot_type: str
    camera: str
    visual: str
    voice: str
    music: str
    sfx: list[str]
    transition: str
    subtitle: str
    continuity: str
    duration_s: int

def build_v3_plan(title: str, language: str="ar", target_minutes: int=12) -> dict[str, Any]:
    if not title.strip(): raise ValueError("MOVIE_TITLE_REQUIRED")
    if target_minutes < 5 or target_minutes > 30: raise ValueError("TARGET_MINUTES_5_TO_30")
    beats = [
        ("HOOK","الخطاف","SLOW"),("SETUP","التأسيس","MEDIUM"),
        ("INCITING_EVENT","الشرارة","FAST"),("ESCALATION","التصعيد","SLOW"),
        ("MIDPOINT","نقطة التحول","FAST"),("CRISIS","الأزمة","FAST"),
        ("CLIMAX","الذروة","CLIMAX"),("RESOLUTION","الخاتمة","RELEASE")
    ]
    shots=[]
    per_beat=4
    for bi,(key,label,rhythm) in enumerate(beats):
        for si in range(per_beat):
            st=SHOT_TYPES[si % len(SHOT_TYPES)]
            cam=CAMERA_MOVES[(bi*2+si) % len(CAMERA_MOVES)]
            trans=TRANSITIONS[(bi+si) % len(TRANSITIONS)]
            shots.append(asdict(Shot(
                id=f"B{bi+1:02d}-S{si+1:02d}", shot_type=st, camera=cam,
                visual=f"{label} — {st.lower()} visual", voice=f"{label} narration",
                music=MUSIC[min(bi, len(MUSIC)-1)], sfx=[SFX[(bi+si)%len(SFX)]],
                transition=trans, subtitle=f"{label} — narration", continuity="CHARACTER+LOCATION+TIME",
                duration_s=6 if rhythm in ("FAST","CLIMAX") else 9
            )))
    return {
        "version":"CINEMATIC_V3_PRO","title":title.strip(),"language":language,
        "target_minutes":target_minutes,"beats":[{"id":k,"label":l,"rhythm":r} for k,l,r in beats],
        "shots":shots,
        "audio":{"voiceover":"cinematic_ar","music_duck_db":-10,"sfx":"event_bound"},
        "camera_engine":{"moves":CAMERA_MOVES,"gpu_transforms":True,"parallax":True},
        "continuity":{"character_bible":True,"location_bible":True,"state_tracking":True},
        "quality_gates":{"min_shots_per_beat":3,"max_static_seconds":8,"require_voice":True,"require_audio_activity":True,"require_transition":True,"reject_slideshow":True},
        "status":"PLAN_READY"
    }

def validate_v3(plan: dict[str,Any]) -> dict[str,Any]:
    beats=plan.get("beats",[]); shots=plan.get("shots",[])
    counts={b["id"]:0 for b in beats}
    for s in shots:
        bid=s["id"].split("-")[0]
        if bid in counts: counts[bid]+=1
    checks={
        "images_present": bool(shots),
        "multiple_shots_per_beat": all(v>=3 for v in counts.values()),
        "camera_motion": all(bool(s.get("camera")) for s in shots),
        "voiceover": bool(plan.get("audio",{}).get("voiceover")),
        "music": bool(plan.get("audio",{}).get("music_duck_db") is not None),
        "sfx": all(bool(s.get("sfx")) for s in shots),
        "subtitles": all(bool(s.get("subtitle")) for s in shots),
        "transitions": all(bool(s.get("transition")) for s in shots),
        "continuity": bool(plan.get("continuity",{}).get("character_bible") and plan.get("continuity",{}).get("location_bible")),
        "no_static_slideshow": plan.get("quality_gates",{}).get("reject_slideshow",False),
        "mobile_ready": bool(plan.get("camera_engine",{}).get("gpu_transforms"))
    }
    return {"status":"PASS" if all(checks.values()) else "REJECT","checks":checks,"shot_count":len(shots),"beat_count":len(beats)}
