"""Safe runtime bridge for Brain optional open-source services."""
from __future__ import annotations
import json, os, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def _get(url: str, timeout: float = 5):
    try:
        req=Request(url, headers={"User-Agent":"Brain-OSS-Runtime/1.0"})
        with urlopen(req, timeout=timeout) as response:
            return {"available": True, "status": int(getattr(response, "status", 200))}
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {"available": False, "error": str(exc)[:180]}

def collect_status():
    services = [
        ("ollama", os.getenv("BRAIN_OLLAMA_URL", "http://127.0.0.1:11434") + "/api/tags"),
        ("comfyui", os.getenv("BRAIN_COMFYUI_URL", "http://127.0.0.1:8188") + "/system_stats"),
        ("qdrant", os.getenv("BRAIN_QDRANT_URL", "http://127.0.0.1:6333") + "/readyz"),
        ("llama_cpp", os.getenv("BRAIN_LLAMA_CPP_URL", "http://127.0.0.1:8080") + "/health"),
    ]
    report={
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "autostart_enabled": os.getenv("BRAIN_OSS_AUTOSTART", "false").lower()=="true",
        "policy": {"download_models": False, "autostart_default": False, "core_brain_requires_oss": False},
        "services": [{"id": i, "url": u, "health": _get(u)} for i,u in services],
    }
    out=Path(os.getenv("BRAIN_OSS_ARTIFACT_DIR","brain6_artifacts"))
    out.mkdir(exist_ok=True)
    (out/"open_source_runtime_status.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

if __name__=="__main__":
    r=collect_status()
    print(json.dumps({"ok":True,"services":len(r["services"]),"available":sum(x["health"]["available"] for x in r["services"])}))
