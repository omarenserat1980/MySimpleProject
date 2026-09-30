"""Small HTTP adapters for optional Brain open-source backends.

Adapters are dependency-free and never install or download models.
"""
from __future__ import annotations
import json
from urllib.request import Request, urlopen

class JSONAPI:
    def __init__(self, base_url: str, timeout: float = 10):
        self.base=base_url.rstrip("/")
        self.timeout=timeout

    def request(self, method: str, path: str, payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        headers={"User-Agent":"Brain-OSS-Adapter/1.0"}
        if data is not None:
            headers["Content-Type"]="application/json"
        req=Request(self.base+path,data=data,headers=headers,method=method)
        with urlopen(req,timeout=self.timeout) as response:
            raw=response.read().decode("utf-8")
            return json.loads(raw) if raw else {}

class OllamaAdapter(JSONAPI):
    def models(self):
        return self.request("GET","/api/tags")
    def generate(self, model: str, prompt: str):
        return self.request("POST","/api/generate",{"model":model,"prompt":prompt,"stream":False})

class ComfyUIAdapter(JSONAPI):
    def system_stats(self):
        return self.request("GET","/system_stats")
    def queue_prompt(self, workflow: dict, client_id: str="brain"):
        return self.request("POST","/prompt",{"prompt":workflow,"client_id":client_id})

class QdrantAdapter(JSONAPI):
    def ready(self):
        return self.request("GET","/readyz")

class LlamaCppAdapter(JSONAPI):
    def health(self):
        return self.request("GET","/health")
