from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3

from . import service
from .merge import merge_branch
from .service import BrainGitError, repository_path


@dataclass(frozen=True)
class PullRequest:
    id: int
    namespace: str
    repository: str
    source: str
    target: str
    title: str
    status: str = "open"
    merged_sha: str | None = None


def _init() -> None:
    service.initialize()
    with sqlite3.connect(service.DB) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS pull_requests(
          id INTEGER PRIMARY KEY AUTOINCREMENT, namespace TEXT, repository TEXT,
          source TEXT, target TEXT, title TEXT, status TEXT, created_at TEXT,
          merged_sha TEXT)""")
        db.commit()


def create_pull_request(namespace: str, repository: str, source: str, target: str, title: str) -> PullRequest:
    if source == target:
        raise BrainGitError("source and target must differ")
    _init()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(service.DB) as db:
        cur = db.execute(
            """INSERT INTO pull_requests(namespace,repository,source,target,title,status,created_at)
               VALUES(?,?,?,?,?,'open',?)""",
            (namespace, repository, source, target, title, now),
        )
        db.commit()
        return PullRequest(cur.lastrowid, namespace, repository, source, target, title)


def close_pull_request(pr_id: int) -> None:
    _init()
    with sqlite3.connect(service.DB) as db:
        cur = db.execute("UPDATE pull_requests SET status='closed' WHERE id=? AND status='open'", (pr_id,))
        if cur.rowcount != 1:
            raise BrainGitError("pull request not found or not open")
        db.commit()


def merge_pull_request(pr_id: int) -> PullRequest:
    _init()
    with sqlite3.connect(service.DB) as db:
        row = db.execute(
            "SELECT id,namespace,repository,source,target,title,status,merged_sha FROM pull_requests WHERE id=?",
            (pr_id,),
        ).fetchone()
    if not row:
        raise BrainGitError("pull request not found")
    pr = PullRequest(*row)
    if pr.status != "open":
        raise BrainGitError("pull request is not open")

    sha = merge_branch(repository_path(pr.namespace, pr.repository), pr.source, pr.target)
    with sqlite3.connect(service.DB) as db:
        db.execute("UPDATE pull_requests SET status='merged', merged_sha=? WHERE id=?", (sha, pr_id))
        db.commit()
    return PullRequest(pr.id, pr.namespace, pr.repository, pr.source, pr.target, pr.title, "merged", sha)
