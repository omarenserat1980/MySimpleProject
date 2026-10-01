"""Evidence-based cinema completion gate. No process exit code alone can prove completion."""
from __future__ import annotations
import hashlib, json, os, subprocess, time
from pathlib import Path

class FilmCompletionGate:
    REQUIRED = "VERIFIED_COMPLETED"
    DEFAULT_TARGET_SECONDS = 7200.0
    DEFAULT_WIDTH = 1000
    DEFAULT_HEIGHT = 650

    def __init__(self, film_root):
        self.root = Path(film_root)

    def _probe(self, final):
        p = subprocess.run([
            "ffprobe","-v","error","-show_entries",
            "format=duration:stream=codec_type,width,height,codec_name",
            "-of","json",str(final)], text=True, capture_output=True, timeout=120)
        if p.returncode != 0:
            return {"ok": False, "error": (p.stderr or p.stdout)[-2000:]}
        try:
            d=json.loads(p.stdout); streams=d.get("streams",[])
            video=[s for s in streams if s.get("codec_type")=="video"]
            audio=[s for s in streams if s.get("codec_type")=="audio"]
            return {"ok":True,"duration":float(d["format"]["duration"]),
                    "video":bool(video),"audio":bool(audio),
                    "width":video[0].get("width") if video else None,
                    "height":video[0].get("height") if video else None,
                    "video_codec":video[0].get("codec_name") if video else None,
                    "audio_codec":audio[0].get("codec_name") if audio else None}
        except Exception as e:
            return {"ok":False,"error":f"FFPROBE_JSON_INVALID:{e}"}

    def _decode_smoke(self, final):
        p=subprocess.run(["ffmpeg","-v","error","-i",str(final),"-map","0:v:0","-map","0:a:0?","-t","5","-f","null","-"],
                         text=True,capture_output=True,timeout=180)
        return {"ok":p.returncode==0,"stderr":p.stderr[-2000:]}

    def check(self):
        final=self.root/"final.mp4"; manifest=self.root/"manifest.json"; marker=self.root/self.REQUIRED
        reasons=[]; probe={"ok":False}; decode={"ok":False}; data={}
        target=float(os.getenv("BRAIN_FILM_TARGET_SECONDS",str(self.DEFAULT_TARGET_SECONDS)))
        width=int(os.getenv("BRAIN_FILM_WIDTH",str(self.DEFAULT_WIDTH)))
        height=int(os.getenv("BRAIN_FILM_HEIGHT",str(self.DEFAULT_HEIGHT)))
        tolerance=max(2.0,min(10.0,target*0.01))
        if not final.is_file(): reasons.append("FINAL_MP4_MISSING")
        if not manifest.is_file(): reasons.append("MANIFEST_MISSING")
        if not marker.is_file(): reasons.append("VERIFIED_MARKER_MISSING")
        if final.is_file():
            probe=self._probe(final)
            if not probe.get("ok"): reasons.append("FFPROBE_FAILED")
            else:
                if not probe.get("video"): reasons.append("VIDEO_STREAM_MISSING")
                if not probe.get("audio"): reasons.append("AUDIO_STREAM_MISSING")
                if probe.get("width")!=width or probe.get("height")!=height: reasons.append("RESOLUTION_MISMATCH")
                if abs(probe.get("duration",0)-target)>tolerance: reasons.append("DURATION_MISMATCH")
                if probe.get("duration",0)<=1: reasons.append("INVALID_DURATION")
                decode=self._decode_smoke(final)
                if not decode.get("ok"): reasons.append("DECODE_SMOKE_FAILED")
        if manifest.is_file():
            try: data=json.loads(manifest.read_text(encoding="utf-8"))
            except Exception: reasons.append("MANIFEST_INVALID")
        if data.get("status")!=self.REQUIRED: reasons.append("MANIFEST_NOT_VERIFIED")
        if data.get("final") and Path(str(data["final"])).name!=final.name: reasons.append("MANIFEST_FINAL_MISMATCH")
        mq=data.get("master_qc") or {}
        if mq:
            if probe.get("ok") and abs(float(mq.get("duration",0))-probe.get("duration",0))>0.5: reasons.append("MASTER_QC_DURATION_MISMATCH")
            if mq.get("width")!=probe.get("width") or mq.get("height")!=probe.get("height"): reasons.append("MASTER_QC_GEOMETRY_MISMATCH")
        else: reasons.append("MASTER_QC_MISSING")
        if data.get("parts") and len(data.get("parts_manifest",[]))<int(data["parts"]): reasons.append("PART_EVIDENCE_INCOMPLETE")
        sha=None
        if final.is_file():
            h=hashlib.sha256();
            with final.open("rb") as fh:
                for chunk in iter(lambda:fh.read(1024*1024),b""): h.update(chunk)
            sha=h.hexdigest()
        result={"completed":not reasons,"status":"COMPLETED" if not reasons else "INCOMPLETE","checked_at":time.time(),
                "final_mp4":str(final) if final.is_file() else None,"sha256":sha,"target_seconds":target,
                "tolerance_seconds":tolerance,"expected_resolution":[width,height],"probe":probe,"decode_smoke":decode,
                "manifest_status":data.get("status"),"master_qc_present":bool(mq),"reasons":reasons}
        self.root.mkdir(parents=True,exist_ok=True)
        (self.root/"completion_gate.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        return result
