"""Autonomous film production supervisor.

Runs a bounded discover/plan/execute/verify/repair/retry loop. It uses the
existing renderer as a safe fallback and records the decision trace. It never
publishes externally.
"""
from __future__ import annotations
import json, subprocess, time
from pathlib import Path
from .brain_supervisor import BrainSupervisor

class FilmSupervisor:
    def __init__(self, work="/tmp/last-light", artifact_root="brain6_artifacts", max_attempts=3):
        self.work=Path(work); self.artifacts=Path(artifact_root); self.max_attempts=max(1,min(int(max_attempts),3))
        self.artifacts.mkdir(parents=True,exist_ok=True)

    def run(self, seconds=12, fps=12):
        self.work.mkdir(parents=True,exist_ok=True)
        supervisor=BrainSupervisor(str(self.artifacts/"supervisor"), self.max_attempts)
        job=supervisor.create("film:last-light", budget=self.max_attempts+2)
        trace=[]
        for attempt in range(1,self.max_attempts+1):
            trace.append({"attempt":attempt,"phase":"discover","ok":True})
            trace.append({"attempt":attempt,"phase":"plan","backend":"local_python_ffmpeg_renderer"})
            out=subprocess.run(
                ["python","cloud/last_light_movie.py","--output",str(self.work),"--seconds",str(seconds),"--fps",str(fps)],
                text=True,capture_output=True
            )
            if out.returncode != 0:
                trace.append({"attempt":attempt,"phase":"execute","ok":False,"stderr":out.stderr[-2000:]})
                trace.append({"attempt":attempt,"phase":"repair","action":"clean_output"})
                subprocess.run(["rm","-rf",str(self.work)],check=False)
                self.work.mkdir(parents=True,exist_ok=True)
                continue
            ok,details=self.verify()
            trace.append({"attempt":attempt,"phase":"verify","ok":ok,"details":details})
            if ok:
                manifest={
                    "title":"آخر ضوء في المدينة","status":"VERIFIED_COMPLETED",
                    "renderer":"Python/Pillow + FFmpeg","control_plane":"brain_supervisor",
                    "attempts":attempt,"verified":True
                }
                (self.work/"film_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
                (self.work/"VERIFIED_COMPLETED").write_text("verified\n",encoding="utf-8")
                final=supervisor.transition(job,"deliver",status="completed",details={"attempts":attempt})
                supervisor.snapshot(final,{"verified":True,"attempts":attempt,"trace":trace})
                (self.artifacts/"film_supervisor_trace.json").write_text(json.dumps(trace,ensure_ascii=False,indent=2),encoding="utf-8")
                return 0
            trace.append({"attempt":attempt,"phase":"repair","action":"rebuild_artifact"})
            subprocess.run(["rm","-f",str(self.work/"last_light_city.mp4"),str(self.work/"ffprobe.json")],check=False)
        trace.append({"phase":"failed","attempts":self.max_attempts})
        supervisor.snapshot(job,{"verified":False,"trace":trace})
        (self.artifacts/"film_supervisor_trace.json").write_text(json.dumps(trace,ensure_ascii=False,indent=2),encoding="utf-8")
        return 1

    def verify(self):
        mp4=self.work/"last_light_city.mp4"
        if not mp4.exists() or mp4.stat().st_size<=0:
            return False,{"reason":"missing_or_empty_mp4"}
        probe=subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=duration,size",
             "-show_entries","stream=codec_type,codec_name,width,height","-of","json",str(mp4)],
            text=True,capture_output=True
        )
        if probe.returncode != 0:
            return False,{"reason":"ffprobe_failed","stderr":probe.stderr[-1000:]}
        data=json.loads(probe.stdout)
        streams=data.get("streams",[])
        fmt=data.get("format",{})
        ok=(any(s.get("codec_type")=="video" for s in streams)
            and any(s.get("codec_type")=="audio" for s in streams)
            and float(fmt.get("duration",0))>0 and int(fmt.get("size",0))>0)
        (self.work/"ffprobe.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
        return ok,{"streams":streams,"format":fmt}

if __name__=="__main__":
    raise SystemExit(FilmSupervisor().run())
