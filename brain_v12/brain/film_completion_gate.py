"""Evidence-based cinema completion gate."""
from __future__ import annotations
import json, subprocess, time
from pathlib import Path

class FilmCompletionGate:
    REQUIRED = "VERIFIED_COMPLETED"
    def __init__(self, film_root):
        self.root = Path(film_root)

    def check(self):
        final = self.root / "final.mp4"
        manifest = self.root / "manifest.json"
        marker = self.root / self.REQUIRED
        reasons = []
        probe = {"ok": False}

        if not final.is_file(): reasons.append("FINAL_MP4_MISSING")
        if not manifest.is_file(): reasons.append("MANIFEST_MISSING")
        if not marker.is_file(): reasons.append("VERIFIED_MARKER_MISSING")

        if final.is_file():
            p = subprocess.run(
                ["ffprobe","-v","error","-show_entries",
                 "format=duration:stream=codec_type,width,height",
                 "-of","json",str(final)],
                text=True, capture_output=True, timeout=120)
            if p.returncode != 0:
                reasons.append("FFPROBE_FAILED")
            else:
                try:
                    d = json.loads(p.stdout)
                    streams = d.get("streams", [])
                    video = [s for s in streams if s.get("codec_type") == "video"]
                    audio = [s for s in streams if s.get("codec_type") == "audio"]
                    probe = {
                        "ok": True,
                        "duration": float(d["format"]["duration"]),
                        "video": bool(video),
                        "audio": bool(audio),
                        "width": video[0].get("width") if video else None,
                        "height": video[0].get("height") if video else None
                    }
                    if not video: reasons.append("VIDEO_STREAM_MISSING")
                    if not audio: reasons.append("AUDIO_STREAM_MISSING")
                    if probe["duration"] < 1: reasons.append("INVALID_DURATION")
                except Exception:
                    reasons.append("FFPROBE_JSON_INVALID")

        data = {}
        if manifest.is_file():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except Exception:
                reasons.append("MANIFEST_INVALID")
        if data.get("status") != self.REQUIRED:
            reasons.append("MANIFEST_NOT_VERIFIED")

        result = {
            "completed": not reasons,
            "status": "COMPLETED" if not reasons else "INCOMPLETE",
            "checked_at": time.time(),
            "final_mp4": str(final) if final.is_file() else None,
            "probe": probe,
            "reasons": reasons
        }
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "completion_gate.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
