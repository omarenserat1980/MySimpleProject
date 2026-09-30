"""Deterministic router from Brain tasks to optional open-source backends."""
from __future__ import annotations
from .open_source_stack import capabilities

TASKS={
 "video_generation":["comfyui","ltx2"],
 "speech_to_text":["whisper"],
 "local_reasoning":["ollama","llama_cpp"],
 "semantic_memory":["qdrant"],
 "realtime_voice_video":["livekit_agents"],
}

def candidates(task:str):
    ids=TASKS.get(task,[])
    by_id={x["id"]:x for x in capabilities()}
    return [by_id[i] for i in ids if i in by_id]

def route(task:str, available_ids:set[str]|None=None):
    pool=candidates(task)
    if available_ids is None:
        return {"task":task,"candidates":pool,"selected":None,
                "reason":"availability must be probed before activation"}
    ready=[x for x in pool if x["id"] in available_ids]
    return {"task":task,"candidates":pool,
            "selected":ready[0] if ready else None,
            "reason":"first compatible available backend" if ready else "no compatible backend available"}

if __name__=="__main__":
    import json
    print(json.dumps({k:[x["id"] for x in candidates(k)] for k in TASKS},indent=2))
