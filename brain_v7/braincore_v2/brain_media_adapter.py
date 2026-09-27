"""Provider-neutral media adapter for Electronic Brain Cinematic Factory.

No Render dependency. The factory talks to any authorized media provider
through MEDIA_PROVIDER_URL and persists provider job metadata for resume.
"""
from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import Any
import httpx

class BrainMediaProvider:
    def __init__(self) -> None:
        self.url=os.getenv("MEDIA_PROVIDER_URL","").strip()
        self.key=os.getenv("MEDIA_PROVIDER_API_KEY","").strip()
        self.timeout=float(os.getenv("MEDIA_PROVIDER_TIMEOUT_SECONDS","900"))
        self.poll=float(os.getenv("MEDIA_PROVIDER_POLL_SECONDS","8"))
        self.max_polls=max(1,int(os.getenv("MEDIA_PROVIDER_MAX_POLLS","120")))

    def _headers(self):
        return {"Authorization": f"Bearer {self.key}"} if self.key else {}

    def render(self, *, shot: dict[str, Any], authorized: bool=False) -> dict[str, Any]:
        if not authorized:
            return {"status":"AUTHORIZATION_REQUIRED"}
        if not self.url:
            return {"status":"MEDIA_PROVIDER_NOT_CONFIGURED"}
        payload={"operation":"generate","shot":shot,
                 "prompt":shot.get("visual_prompt",""),
                 "audio_prompt":shot.get("audio_prompt",""),
                 "shot_id":shot.get("shot_id")}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r=client.post(self.url,json=payload,headers=self._headers())
                r.raise_for_status()
                data=r.json()
                ref=data.get("video_ref") or data.get("output_url") or data.get("media_url")
                status=str(data.get("status","")).upper()
                if ref and status in {"COMPLETED","VERIFIED_COMPLETED","SUCCEEDED","SUCCESS"}:
                    return {"status":"VERIFIED_COMPLETED","video_ref":ref,"provider_result":data,"shot_id":shot.get("shot_id")}
                job_id=data.get("job_id") or data.get("id")
                if not job_id:
                    return {"status":"SUBMISSION_UNVERIFIED","provider_result":data}
                for _ in range(self.max_polls):
                    time.sleep(self.poll)
                    p=client.post(self.url,json={"operation":"status","job_id":job_id},
                                  headers=self._headers())
                    p.raise_for_status()
                    data=p.json()
                    ref=data.get("video_ref") or data.get("output_url") or data.get("media_url")
                    status=str(data.get("status","")).upper()
                    if ref and status in {"COMPLETED","VERIFIED_COMPLETED","SUCCEEDED","SUCCESS"}:
                        return {"status":"VERIFIED_COMPLETED","video_ref":ref,
                                "provider_result":data,"job_id":job_id,"shot_id":shot.get("shot_id")}
                    if status in {"FAILED","ERROR","CANCELLED"}:
                        return {"status":"PROVIDER_FAILED","provider_result":data,"job_id":job_id}
                return {"status":"PROVIDER_TIMEOUT","job_id":job_id}
        except Exception as exc:
            return {"status":"PROVIDER_ERROR","error":repr(exc),"shot_id":shot.get("shot_id")}

class FactoryState:
    def __init__(self, path: str | Path=".factory_state.json") -> None:
        self.path=Path(path)
        self.data={"version":1,"shots":{},"updated_at":None}
        if self.path.is_file():
            try: self.data=json.loads(self.path.read_text(encoding="utf-8"))
            except Exception: pass

    def verified(self, shot_id: str):
        item=self.data.get("shots",{}).get(shot_id,{})
        return item if item.get("status")=="VERIFIED_COMPLETED" and item.get("video_ref") else None

    def save(self, shot_id: str, result: dict[str,Any]):
        self.data.setdefault("shots",{})[shot_id]=result
        self.data["updated_at"]=time.time()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(json.dumps(self.data,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
