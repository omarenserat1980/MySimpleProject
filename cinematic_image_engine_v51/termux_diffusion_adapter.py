from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path

class TermuxDiffusionAdapter:
    def __init__(self, executable=None, model='anime', steps=6, threads=4, width=512, height=512):
        self.executable = executable or shutil.which('termux-diffusion')
        self.model = os.environ.get('EB_DIFFUSION_MODEL', model)
        self.steps = int(os.environ.get('EB_DIFFUSION_STEPS', steps))
        self.threads = int(os.environ.get('EB_DIFFUSION_THREADS', threads))
        self.width, self.height = width, height

    def generate(self, prompt, output, metadata=None):
        if not self.executable:
            raise RuntimeError('termux-diffusion CLI not found')
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.executable, 'generate', prompt,
            '-m', self.model, '--cpu',
            '-W', str(self.width), '-H', str(self.height),
            '--steps', str(self.steps), '-t', str(self.threads),
            '-o', str(output)
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or 'termux-diffusion failed').strip()
            raise RuntimeError(f'termux-diffusion exit={proc.returncode}: {detail[-4000:]}')
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError('Invalid generated image')
        return output
