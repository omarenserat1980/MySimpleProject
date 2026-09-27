from __future__ import annotations
from pathlib import Path
from typing import Protocol
from .phone_executor import PhoneExecutor

class ImageAdapter(Protocol):
    def generate(self, prompt: str, output: Path, metadata: dict) -> Path: ...

class CommandImageAdapter:
    """Terminal-agnostic bridge to an Android-local image generator."""
    def __init__(self, executable, executor=None):
        self.executable=executable
        self.executor=executor or PhoneExecutor()

    def generate(self,prompt,output,metadata):
        result=self.executor.image_command(self.executable,prompt,output,metadata.get("executor_options"))
        if not result.ok:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or
                               f"image generator exited with code {result.returncode}")
        if not output.exists() or output.stat().st_size == 0:
            raise RuntimeError("Generator returned success but produced no image output")
        return output
