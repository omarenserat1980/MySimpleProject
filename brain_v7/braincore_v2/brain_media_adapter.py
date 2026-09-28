"""Provider-neutral media adapter for Electronic Brain Cinematic Factory.

No Render dependency. The factory talks to any authorized media provider
through MEDIA_PROVIDER_URL and persists provider job metadata for resume.
"""
from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import Any
import httpx

try:
    from .cinematic_local_renderer import CinematicLocalRenderer
except Exception:
    CinematicLocalRenderer = None

try:
    import fal_client
except Exception:
    fal_client = None

class BrainMediaProvider:
    def __init__(self) -> None:
        self.url=os.getenv("MEDIA_PROVIDER_URL","").strip()
        self.key=os.getenv("MEDIA_PROVIDER_API_KEY","").strip()
        self.timeout=float(os.getenv("MEDIA_PROVIDER_TIMEOUT_SECONDS","900"))
        self.poll=float(os.getenv("MEDIA_PROVIDER_POLL_SECONDS","8"))
        self.max_polls=max(1,int(os.getenv("MEDIA_PROVIDER_MAX_POLLS","120")))
        # Reuse one HTTP connection pool across concurrent shots. This removes
        # repeated TLS/TCP setup while leaving generation/QC unchanged.
        self._client=httpx.Client(timeout=self.timeout, limits=httpx.Limits(
            max_connections=max(8, int(os.getenv("MEDIA_PROVIDER_HTTP_CONNECTIONS","32"))),
            max_keepalive_connections=max(4, int(os.getenv("MEDIA_PROVIDER_HTTP_KEEPALIVE","16"))),
        ))

    def _headers(self):
        return {"Authorization": f"Bearer {self.key}"} if self.key else {}

    def _render_fal(self, shot: dict[str, Any]) -> dict[str, Any]:
        if fal_client is None:
            return {"status":"FAL_CLIENT_MISSING"}
        model=os.getenv("FAL_MODEL","").strip() or "fal-ai/kling-video/v3/pro/text-to-video"
        duration=str(int(shot.get("duration_s") or os.getenv("FAL_SHOT_DURATION","5")))
        generate_audio=os.getenv("FAL_GENERATE_AUDIO","0").strip().lower() in {"1","true","yes","on"}
        try:
            visual = str(shot.get("visual_prompt", "")).strip()
            audio = str(shot.get("audio_prompt", "")).strip()
            sound = str(shot.get("sound_design_prompt", "")).strip()
            voice = str(shot.get("voice_prompt", "")).strip()
            audio_directive = " ".join(x for x in (audio, sound, voice) if x)
            prompt = visual
            if audio_directive:
                prompt += " Native audio direction: " + audio_directive
            result=fal_client.subscribe(model, arguments={"input":{
                "prompt":prompt,
                "duration":duration,
                "generate_audio":generate_audio,
                "shot_type":"intelligent",
                "aspect_ratio":shot.get("aspect_ratio","16:9"),
                "negative_prompt":shot.get("negative_prompt","blur, distort, low quality, black frames, blank screen, empty scene"),
            }})
            video=((result or {}).get("video") or {})
            ref=video.get("url")
            if not ref:
                return {"status":"SUBMISSION_UNVERIFIED","provider_result":result}
            vision=self._vision_qc_fal(ref,shot)
            return {"status":"VERIFIED_COMPLETED","video_ref":ref,"vision_qc":vision,
                    "provider_result":result,"shot_id":shot.get("shot_id"),
                    "provider":"fal","model":model}
        except Exception as exc:
            message = repr(exc)
            quota_blocked = any(token in message.lower() for token in (
                "exhausted balance", "user is locked", "403 forbidden", "status_code=403"
            ))
            local_enabled = os.getenv("FACTORY_ALLOW_LOCAL_FALLBACK", "0").strip().lower() in {
                "1", "true", "yes", "on"
            }
            if quota_blocked and local_enabled and CinematicLocalRenderer is not None:
                local = CinematicLocalRenderer().render(shot=shot, authorized=True)
                if local.get("status") == "VERIFIED_COMPLETED":
                    return {
                        **local,
                        "provider": "local_ffmpeg_cinematic",
                        "fallback_reason": "fal_quota_blocked",
                        "fal_error": message,
                    }
            return {"status":"PROVIDER_ERROR","error":message,"shot_id":shot.get("shot_id"),
                    "provider":"fal","model":model}

    def _vision_qc_fal(self, video_url: str, shot: dict[str, Any]) -> dict[str, Any] | None:
        if fal_client is None or os.getenv("FAL_VISION_QC","1").strip().lower() not in {"1","true","yes","on"}:
            return None
        prompt = (
            "Evaluate this generated cinematic shot against the requested visual prompt and continuity anchors. "
            "Return ONLY JSON with keys score, status, identity, world, prompt_alignment, issues. "
            "score must be 0..1. status must be PASS or FAIL. "
            "Check subject identity/appearance consistency, wardrobe, world/geography, lighting continuity, "
            "composition/camera intent, anatomy/artifacts, and whether the requested action actually occurs. "
            "Do not invent details that cannot be observed."
        )
        try:
            result=fal_client.subscribe("fal-ai/video-understanding", arguments={"input":{
                "video_url":video_url,
                "prompt":prompt + "\nREQUESTED SHOT:\n" + shot.get("visual_prompt",""),
                "detailed_analysis":True,
            }})
            raw=(result or {}).get("output") or (result or {}).get("data",{}).get("output","")
            parsed=raw
            if isinstance(raw,str):
                text=raw.strip()
                try:
                    parsed=json.loads(text)
                except Exception:
                    start=text.find("{"); end=text.rfind("}")
                    try:
                        parsed=json.loads(text[start:end+1]) if start >= 0 and end > start else None
                    except Exception:
                        parsed=None
            if isinstance(parsed,dict):
                try:
                    parsed["score"]=max(0.0,min(1.0,float(parsed.get("score",0.0))))
                except Exception:
                    parsed["score"]=0.0
                parsed.setdefault("status","FAIL")
                parsed.setdefault("issues",[])
                return parsed
            return {"score":0.0,"status":"FAIL","issues":["vision_output_not_json"],"raw":str(raw)}
        except Exception as exc:
            return {"score":0.0,"status":"FAIL","issues":["vision_qc_error",repr(exc)]}

    def render(self, *, shot: dict[str, Any], authorized: bool=False) -> dict[str, Any]:
        if not authorized:
            return {"status":"AUTHORIZATION_REQUIRED"}
        forced_route = os.getenv("FACTORY_MEDIA_ROUTE", "").strip().lower()
        local_enabled = os.getenv("FACTORY_ALLOW_LOCAL_FALLBACK", "0").strip().lower() in {
            "1", "true", "yes", "on"
        }
        if forced_route == "local_ffmpeg_cinematic" and local_enabled and CinematicLocalRenderer is not None:
            return {
                **CinematicLocalRenderer().render(shot=shot, authorized=True),
                "provider": "local_ffmpeg_cinematic",
                "fallback_reason": "repair_app_route",
            }
        if os.getenv("FAL_KEY","").strip():
            return self._render_fal(shot)
        if not self.url:
            return {"status":"MEDIA_PROVIDER_NOT_CONFIGURED"}
        payload={"operation":"generate","shot":shot,
                 "prompt":shot.get("visual_prompt",""),
                 "audio_prompt":shot.get("audio_prompt",""),
                 "sound_design_prompt":shot.get("sound_design_prompt",""),
                 "voice_prompt":shot.get("voice_prompt",""),
                 "image_reference_prompt":shot.get("image_reference_prompt",""),
                 "negative_prompt":shot.get("negative_prompt",""),
                 "shot_id":shot.get("shot_id")}
        try:
            client=self._client
            r=client.post(self.url,json=payload,headers=self._headers())
            r.raise_for_status()
            data=r.json()
            ref=data.get("video_ref") or data.get("output_url") or data.get("media_url")
            status=str(data.get("status","")).upper()
            if ref and status in {"COMPLETED","VERIFIED_COMPLETED","SUCCEEDED","SUCCESS"}:
                vision=self._vision_qc_fal(ref,shot)
                return {"status":"VERIFIED_COMPLETED","video_ref":ref,"vision_qc":vision,
                        "provider_result":data,"shot_id":shot.get("shot_id"),
                        "provider":"media_provider"}
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
                    vision=self._vision_qc_fal(ref,shot)
                    return {"status":"VERIFIED_COMPLETED","video_ref":ref,"vision_qc":vision,
                            "provider_result":data,"job_id":job_id,"shot_id":shot.get("shot_id"),
                            "provider":"media_provider"}
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
        provider = str(item.get("provider") or "").strip().lower()
        real_providers = {"fal", "comfyui", "media_provider", "local_ffmpeg_cinematic"}
        return (
            item
            if item.get("status") == "VERIFIED_COMPLETED"
            and item.get("video_ref")
            and provider in real_providers
            else None
        )

    def save(self, shot_id: str, result: dict[str,Any]):
        self.data.setdefault("shots",{})[shot_id]=result
        self.data["updated_at"]=time.time()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(json.dumps(self.data,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
