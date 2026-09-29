from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from .service import ROOT, BrainGitError

DB=ROOT/"brain-git.db"

@dataclass(frozen=True)
class PullRequest:
    id:int
    namespace:str
    repository:str
    source:str
    target:str
    title:str
    status:str="open"

def create_pull_request(namespace:str, repository:str, source:str, target:str, title:str)->PullRequest:
    if source==target: raise BrainGitError("source and target must differ")
    with sqlite3.connect(DB) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS pull_requests(
          id INTEGER PRIMARY KEY AUTOINCREMENT, namespace TEXT, repository TEXT,
          source TEXT, target TEXT, title TEXT, status TEXT, created_at TEXT)""")
        cur=db.execute("""INSERT INTO pull_requests(namespace,repository,source,target,title,status,created_at)
                          VALUES(?,?,?,?,?,'open',?)""",
                       (namespace,repository,source,target,title,datetime.now(timezone.utc).isoformat()))
        db.commit()
        return PullRequest(cur.lastrowid,namespace,repository,source,target,title)

def close_pull_request(pr_id:int)->None:
    with sqlite3.connect(DB) as db:
        cur=db.execute("UPDATE pull_requests SET status='closed' WHERE id=?",(pr_id,))
        if cur.rowcount!=1: raise BrainGitError("pull request not found")
        db.commit()
