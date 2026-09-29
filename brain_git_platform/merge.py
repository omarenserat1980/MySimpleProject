from __future__ import annotations
import subprocess
from pathlib import Path
from .service import BrainGitError

def merge_branch(repo: Path, source: str, target: str) -> str:
    if source == target:
        raise BrainGitError("source and target must differ")
    if target in {"main","master"}:
        # Fast-forward only keeps the protected branch deterministic.
        p=subprocess.run(["git","merge-base","--is-ancestor",target,source],cwd=repo,capture_output=True)
        if p.returncode:
            raise BrainGitError("protected branch requires fast-forward")
    p=subprocess.run(["git","merge", "--ff-only", source],cwd=repo,text=True,capture_output=True)
    if p.returncode:
        raise BrainGitError(p.stderr.strip() or "merge failed")
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=repo,text=True,capture_output=True,check=True)
    return head.stdout.strip()
