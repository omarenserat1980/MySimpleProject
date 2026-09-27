from __future__ import annotations
from pathlib import Path
from typing import Protocol

class ImageAdapter(Protocol):
    def generate(self, prompt: str, output: Path, metadata: dict) -> Path: ...

class CommandImageAdapter:
    """Thin bridge to any local Android/Termux image generator."""
    def __init__(self, executable):
        self.executable=executable
    def generate(self,prompt,output,metadata):
        import subprocess
        subprocess.run([self.executable,"--prompt",prompt,"--output",str(output)],check=True)
        return output
