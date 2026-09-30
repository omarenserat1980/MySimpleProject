"""Safe process adapter contract for Qwen-Agent.

The third-party package is never vendored. Configure a reviewed local runner
through BRAIN_QWEN_AGENT_COMMAND after license/security verification.
"""
from __future__ import annotations
import json, os, subprocess

class QwenAgentAdapter:
    def __init__(self, command: str | None = None):
        self.command = command or os.getenv("BRAIN_QWEN_AGENT_COMMAND")

    def run(self, request: dict) -> dict:
        if not self.command:
            return {"status": "UNCONFIGURED", "request": request}
        p = subprocess.run([self.command], input=json.dumps(request), text=True,
                           capture_output=True, timeout=300)
        if p.returncode:
            return {"status":"FAILED","stderr":p.stderr[-4000:]}
        try: result=json.loads(p.stdout)
        except json.JSONDecodeError: result={"output":p.stdout.strip()}
        return {"status":"COMPLETED","result":result}
