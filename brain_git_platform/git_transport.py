from __future__ import annotations
import re
from pathlib import Path
from urllib.parse import unquote
from .service import repository_path, BrainGitError

_REPO = re.compile(r"^/git/([^/]+)/([^/]+?)(?:\.git)?/?$")

def resolve_repo_path(request_path: str) -> Path:
    m = _REPO.match(unquote(request_path))
    if not m:
        raise BrainGitError("invalid repository path")
    return repository_path(m.group(1), m.group(2))

def upload_pack(repo: Path, input_data: bytes) -> bytes:
    import subprocess
    p = subprocess.run(["git", "upload-pack", "--stateless-rpc", str(repo)],
                       input=input_data, capture_output=True)
    if p.returncode:
        raise BrainGitError(p.stderr.decode(errors="replace"))
    return p.stdout

def receive_pack(repo: Path, input_data: bytes) -> bytes:
    import subprocess
    p = subprocess.run(["git", "receive-pack", "--stateless-rpc", str(repo)],
                       input=input_data, capture_output=True)
    if p.returncode:
        raise BrainGitError(p.stderr.decode(errors="replace"))
    return p.stdout
