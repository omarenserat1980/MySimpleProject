from __future__ import annotations
import json, os, shutil, uuid
from pathlib import Path
from .state import StateManager
from .router import LocalModelRouter
from .planner import decompose_script, plan_shots
from .qc import CinematicQC
from .adapter import CommandImageAdapter
from .local_runtime import discover_runtime

class ImageFactory:
    def __init__(self,project_dir,config=None,max_retries=5):
        self.root=Path(project_dir); self.root.mkdir(parents=True,exist_ok=True)
        for d in ("characters","world","style","scenes","shots","master","qc","candidates","cache"):
            (self.root/d).mkdir(exist_ok=True)
        self.config=config or {}
        self.state_mgr=StateManager(project_dir)
        self.router=LocalModelRouter(self.config)
        self.qc=CinematicQC()
        self.max_retries=max_retries
        self.runtime=discover_runtime(self.config)

    def initialize(self,project_id=None):
        return self.state_mgr.load(project_id or f"EB-{uuid.uuid4().hex[:12]}")

    def prepare(self,state,script):
        scenes=decompose_script(script); shots=plan_shots(scenes)
        for s in shots: state.shots.setdefault(s.shot_id,s.__dict__)
        (self.root/"scenes"/"scenes.json").write_text(json.dumps(scenes,ensure_ascii=False,indent=2),encoding="utf-8")
        state.operations["SCRIPT_DECOMPOSITION"]="VERIFIED"
        state.operations["SHOT_PLANNING"]="VERIFIED"
        self.state_mgr.save(state); return shots

    def build_prompt(self,shot,state):
        c=state.continuity
        return "\n".join([
            "CINEMATIC IMAGE MASTER PROMPT",
            f"STYLE_DNA: {state.model_info.get('style_dna','cinematic photorealism')}",
            f"WORLD_DNA: {c.get('world_dna','')}",
            f"CHARACTER_DNA: {c.get('character_dna','')}",
            f"CURRENT_STATE: {json.dumps(c,ensure_ascii=False)}",
            f"SHOT: {shot['purpose']} | {shot['action']}",
            f"CAMERA: {shot['camera']} {shot['lens']}",
            f"LOCATION: {shot['location']}",
            f"EMOTION: {shot['emotion']}"
        ])

    def generate(self,shot,prompt,attempt):
        if not self.runtime:
            raise RuntimeError("No local image generator found. Set EB_IMAGE_ADAPTER to a real Android/Termux generator.")
        route=self.router.choose(shot.get("camera","medium"),"preview")
        executable=route.get("executable") or route.get("path") or self.runtime[0]["executable"]
        out=self.root/"candidates"/f"{shot['shot_id']}_attempt{attempt:02d}.png"
        return CommandImageAdapter(executable).generate(prompt,out,{
            "shot": shot, "attempt": attempt, "route": route
        })

    def run(self,state):
        state.model_info["runtime_discovery"]=self.runtime
        for shot_id,shot in state.shots.items():
            if self.state_mgr.verified(state,shot_id): continue
            prompt=self.build_prompt(shot,state)
            state.model_info["last_route"]=self.router.choose(shot.get("camera","medium"),"preview")
            success=False
            for attempt in range(1,self.max_retries+1):
                shot["attempts"]=attempt
                try:
                    candidate=self.generate(shot,prompt,attempt)
                    qc=self.qc.inspect(candidate,shot,state.continuity)
                except Exception as exc:
                    qc={"pass":False,"error":str(exc)}
                shot["qc"]=qc
                if qc["pass"]:
                    master=self.root/"master"/f"{shot_id}.png"
                    shutil.copy2(candidate,master)
                    shot["master_file"]=str(master); shot["status"]="VERIFIED"
                    state.continuity.update({
                        "last_shot":shot_id,
                        "location":shot.get("location",""),
                        "emotion":shot.get("emotion",""),
                        "camera":shot.get("camera","")
                    })
                    state.operations[f"SHOT:{shot_id}"]="VERIFIED"
                    state.last_completed_operation=f"SHOT:{shot_id}"
                    success=True
                    break
            if not success:
                shot["status"]="NEEDS_REVIEW"
                state.operations[f"SHOT:{shot_id}"]="NEEDS_REVIEW"
            self.state_mgr.save(state)
        state.status="COMPLETE" if all(s.get("status")=="VERIFIED" for s in state.shots.values()) else "NEEDS_REVIEW"
        self.state_mgr.save(state)
        self.write_manifest(state)
        return state

    def write_manifest(self,state):
        manifest={
            "PROJECT_ID":state.project_id,
            "VERSION":state.version,
            "STATUS":state.status,
            "SHOTS":state.shots,
            "MASTER_FILES":[s["master_file"] for s in state.shots.values() if s.get("master_file")],
            "FAILED_SHOTS":[sid for sid,s in state.shots.items() if s.get("status")!="VERIFIED"],
            "MODEL_INFO":state.model_info,
            "CONTINUITY_STATE":state.continuity
        }
        (self.root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
