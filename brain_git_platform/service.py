"""Minimal Brain-native Git service boundary.

This module intentionally has no GitHub dependency. It stores repository metadata
in SQLite and Git repositories as bare repositories under BRAIN_GIT_ROOT.
"""
from __future__ import annotations
import os, sqlite3, subprocess
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(os.environ.get("BRAIN_GIT_ROOT", "./brain_git_data")).resolve()
DB = ROOT / "brain-git.db"

@dataclass(frozen=True)
class Repository:
    namespace: str
    name: str
    default_branch: str = "main"

class BrainGitError(RuntimeError):
    pass

def _run(*args: str, cwd: Path | None = None) -> str:
    p = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if p.returncode:
        raise BrainGitError(p.stderr.strip() or "git command failed")
    return p.stdout.strip()

def initialize() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS repositories(
            namespace TEXT NOT NULL, name TEXT NOT NULL,
            default_branch TEXT NOT NULL, path TEXT NOT NULL UNIQUE,
            PRIMARY KEY(namespace,name))""")
        db.commit()

def create_repository(repo: Repository) -> Path:
    initialize()
    path = ROOT / "repos" / repo.namespace / f"{repo.name}.git"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise BrainGitError("repository already exists")
    _run("git", "init", "--bare", str(path))
    with sqlite3.connect(DB) as db:
        db.execute("INSERT INTO repositories VALUES(?,?,?,?)",
                   (repo.namespace, repo.name, repo.default_branch, str(path)))
        db.commit()
    return path

def repository_path(namespace: str, name: str) -> Path:
    initialize()
    with sqlite3.connect(DB) as db:
        row = db.execute("SELECT path FROM repositories WHERE namespace=? AND name=?",
                         (namespace, name)).fetchone()
    if not row:
        raise BrainGitError("repository not found")
    return Path(row[0])

def health() -> dict:
    initialize()
    _run("git", "--version")
    return {"ok": True, "github_dependency": False, "root": str(ROOT)}
