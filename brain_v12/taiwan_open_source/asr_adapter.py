"""Contract for plugging a Taiwan ASR implementation into Brain.

No third-party implementation is embedded here. The adapter executes a
configured local service/command and returns normalized transcript data.
"""
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path

class TaiwanASRAdapter:
    def __init__(self, command: str | None = None):
        self.command = command or os.getenv("BRAIN_TAIWAN_ASR_COMMAND")

    def transcribe(self, audio: str) -> dict:
        if not self.command:
            return {"status": "UNCONFIGURED", "audio": audio}
        p = subprocess.run(
            [self.command, audio], text=True, capture_output=True, timeout=300
        )
        if p.returncode != 0:
            return {"status": "FAILED", "audio": audio, "stderr": p.stderr[-4000:]}
        try:
            payload = json.loads(p.stdout)
        except json.JSONDecodeError:
            payload = {"text": p.stdout.strip()}
        return {"status": "COMPLETED", "audio": audio, "result": payload}
