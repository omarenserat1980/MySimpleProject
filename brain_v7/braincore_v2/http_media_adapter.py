"""HTTP media renderer and local FFmpeg assembler.

The deployment supplies a media provider endpoint and API key. Provider
response must contain a completed media URL in output_url (or video_ref).
"""
from __future__ import annotations
import os, subprocess, tempfile, urllib.request
from pathlib import Path
from typing import Any, Sequence
import httpx

class HttpShotRenderer:
    def __init__(self) -> None:
        self.url=os.getenv("MEDIA_RENDER_URL","").strip()
        self.key=os.getenv("MEDIA_RENDER_API_KEY","").strip()
        self.timeout=float(os.getenv("MEDIA_RENDER_TIMEOUT_SECONDS","900"))
    def render(self, *, shot: dict[str, Any], authorized: bool=False) -> dict[str, Any]:
        if not authorized:
            return {"status":"AUTHORIZATION_REQUIRED"}
        if not self.url:
            return {"status":"MEDIA_PROVIDER_NOT_CONFIGURED"}
        headers={"Authorization":f"Bearer {self.key}"} if self.key else {}
        with httpx.Client(timeout=self.timeout) as client:
            r=client.post(self.url,json={"prompt":shot.get("visual_prompt",""),"audio_prompt":shot.get("audio_prompt",""),"shot":shot},headers=headers)
            r.raise_for_status()
            data=r.json()
        ref=data.get("video_ref") or data.get("output_url")
        if data.get("status") not in {"COMPLETED","VERIFIED_COMPLETED"} or not ref:
            return {"status":"SUBMISSION_UNVERIFIED","provider_result":data}
        return {"status":"VERIFIED_COMPLETED","video_ref":ref,"provider_result":data,"shot_id":shot.get("shot_id")}

class FfmpegVideoAssembler:
    def __init__(self) -> None:
        self.ffmpeg=os.getenv("FFMPEG_BIN","ffmpeg")
    def assemble(self, *, outputs: Sequence[dict[str,Any]], plan: Any) -> dict[str,Any]:
        if not outputs: return {"status":"ASSEMBLY_BLOCKED","reason":"NO_OUTPUTS"}
        work=Path(tempfile.mkdtemp(prefix="factory_"))
        files=[]
        try:
            for i,item in enumerate(outputs):
                url=item.get("video_ref")
                if not url: return {"status":"ASSEMBLY_BLOCKED","reason":"MISSING_VIDEO_REF"}
                p=work/f"{i:04d}.mp4"
                if str(url).startswith(("http://","https://")):
                    urllib.request.urlretrieve(str(url),p)
                else:
                    src=Path(str(url))
                    if not src.is_file(): return {"status":"ASSEMBLY_BLOCKED","reason":"LOCAL_VIDEO_NOT_FOUND"}
                    p.write_bytes(src.read_bytes())
                files.append(p)
            manifest=work/"concat.txt"
            manifest.write_text("".join(f"file '{p.as_posix()}'\n" for p in files),encoding="utf-8")
            out=work/"final.mp4"
            subprocess.run([self.ffmpeg,"-y","-f","concat","-safe","0","-i",str(manifest),"-c:v","libx264","-preset",os.getenv("LOCAL_FFMPEG_PRESET","veryfast"),"-crf","27","-c:a","aac","-b:a","96k","-movflags","+faststart",str(out)],check=True,capture_output=True,text=True)
            return {"status":"ASSEMBLED","video_ref":str(out),"shot_count":len(files)}
        except Exception as exc:
            return {"status":"ASSEMBLY_BLOCKED","reason":repr(exc)}
