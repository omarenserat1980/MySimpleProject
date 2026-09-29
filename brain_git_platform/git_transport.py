from __future__ import annotations

import re
import subprocess
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
    p = subprocess.run(
        ["git", "upload-pack", "--stateless-rpc", str(repo)],
        input=input_data,
        capture_output=True,
    )
    if p.returncode:
        raise BrainGitError(p.stderr.decode(errors="replace") or "git upload-pack failed")
    return p.stdout


def receive_pack(repo: Path, input_data: bytes) -> bytes:
    p = subprocess.run(
        ["git", "receive-pack", "--stateless-rpc", str(repo)],
        input=input_data,
        capture_output=True,
    )
    if p.returncode:
        raise BrainGitError(p.stderr.decode(errors="replace") or "git receive-pack failed")
    return p.stdout


def advertise_refs(repo: Path, service_name: str) -> bytes:
    if service_name not in {"git-upload-pack", "git-receive-pack"}:
        raise BrainGitError("unsupported git service")
    command = "upload-pack" if service_name == "git-upload-pack" else "receive-pack"
    p = subprocess.run(
        ["git", command, "--stateless-rpc", "--advertise-refs", str(repo)],
        capture_output=True,
    )
    if p.returncode:
        raise BrainGitError(p.stderr.decode(errors="replace") or "git advertise-refs failed")
    service_line = f"# service={service_name}\n".encode("ascii")
    prefix = f"{len(service_line) + 4:04x}".encode("ascii") + service_line + b"0000"
    return prefix + p.stdout
