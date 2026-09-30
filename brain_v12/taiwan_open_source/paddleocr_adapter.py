"""Safe process adapter contract for PaddleOCR."""
from __future__ import annotations
import json, os, subprocess

class PaddleOCRAdapter:
    def __init__(self, command: str | None = None):
        self.command = command or os.getenv("BRAIN_PADDLEOCR_COMMAND")

    def parse(self, document: str) -> dict:
        if not self.command:
            return {"status":"UNCONFIGURED","document":document}
        p=subprocess.run([self.command, document], text=True, capture_output=True, timeout=300)
        if p.returncode:
            return {"status":"FAILED","document":document,"stderr":p.stderr[-4000:]}
        try: result=json.loads(p.stdout)
        except json.JSONDecodeError: result={"output":p.stdout.strip()}
        return {"status":"COMPLETED","document":document,"result":result}
