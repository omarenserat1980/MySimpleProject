from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .service import BrainGitError


def _git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=check)


def merge_branch(repo: Path, source: str, target: str) -> str:
    """Fast-forward a Brain Git branch using an isolated temporary clone."""
    if source == target:
        raise BrainGitError("source and target must differ")

    for branch in (source, target):
        try:
            _git("show-ref", "--verify", f"refs/heads/{branch}", cwd=repo)
        except subprocess.CalledProcessError as exc:
            raise BrainGitError("source or target branch not found") from exc

    temp = Path(tempfile.mkdtemp(prefix="brain-git-merge-"))
    try:
        work = temp / "work"
        _git("clone", "--no-tags", str(repo), str(work))
        _git("checkout", "--quiet", target, cwd=work)

        p = _git("merge", "--ff-only", source, cwd=work, check=False)
        if p.returncode:
            raise BrainGitError(p.stderr.strip() or "merge is not fast-forwardable")

        # A normal push is intentionally non-forcing: concurrent target updates fail.
        p = _git("push", "origin", f"HEAD:refs/heads/{target}", cwd=work, check=False)
        if p.returncode:
            raise BrainGitError(p.stderr.strip() or "target branch changed during merge")

        return _git("rev-parse", "HEAD", cwd=work).stdout.strip()
    finally:
        shutil.rmtree(temp, ignore_errors=True)
