from __future__ import annotations
from pathlib import Path
from .service import BrainGitError

def _check_ref(ref: str) -> None:
    if not ref or ref.startswith("-") or ".." in ref or " " in ref:
        raise BrainGitError("invalid ref")

def list_refs(repo: Path) -> list[str]:
    import subprocess
    p=subprocess.run(["git","for-each-ref","--format=%(refname)","refs/heads/","refs/tags/"],
                     cwd=repo,capture_output=True,text=True)
    if p.returncode: raise BrainGitError(p.stderr.strip())
    return [x for x in p.stdout.splitlines() if x]

def create_branch(repo: Path, name: str, start_point: str = "HEAD") -> None:
    _check_ref(name)
    import subprocess
    p=subprocess.run(["git","branch",name,start_point],cwd=repo,capture_output=True,text=True)
    if p.returncode: raise BrainGitError(p.stderr.strip())

def delete_branch(repo: Path, name: str) -> None:
    _check_ref(name)
    if name in {"main","master"}: raise BrainGitError("protected branch")
    import subprocess
    p=subprocess.run(["git","branch","-D",name],cwd=repo,capture_output=True,text=True)
    if p.returncode: raise BrainGitError(p.stderr.strip())
