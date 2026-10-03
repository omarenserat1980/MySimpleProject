"""Minimal Brain-owned Git service.

Uses the standard Git executable for repository/object correctness while Brain owns
metadata, authorization boundaries, audit records, and workflow integration.
GitHub is not required by this module.
"""
from __future__ import annotations
import hashlib, json, os, sqlite3, subprocess, time, tempfile, shutil
from pathlib import Path
from typing import Any

class BrainGitError(RuntimeError): pass

class BrainGitService:
    def __init__(self, root: str|Path="brain6_artifacts/brain_git"):
        self.root=Path(root); self.repos=self.root/"repos"; self.db_path=self.root/"brain_git.db"
        self.repos.mkdir(parents=True,exist_ok=True); self._init_db()
    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row; return c
    def _init_db(self):
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS repositories(
              id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, path TEXT NOT NULL,
              private INTEGER NOT NULL DEFAULT 1, created_at REAL NOT NULL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS audit(
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, action TEXT NOT NULL,
              repository TEXT, details TEXT NOT NULL, digest TEXT NOT NULL)""")
    def _audit(self,action,repository,details):
        raw=json.dumps({"ts":time.time(),"action":action,"repository":repository,"details":details},sort_keys=True)
        digest=hashlib.sha256(raw.encode()).hexdigest()
        with self._db() as c:c.execute("INSERT INTO audit(ts,action,repository,details,digest) VALUES(?,?,?,?,?)",(time.time(),action,repository,json.dumps(details,sort_keys=True),digest))
    def _run(self,args,cwd=None,input=None):
        p=subprocess.run(["git",*args],cwd=cwd,input=input,text=True,capture_output=True)
        if p.returncode: raise BrainGitError(p.stderr.strip() or p.stdout.strip() or f"git exit {p.returncode}")
        return p.stdout.strip()
    def create_repository(self,name,private=True):
        if not name or "/" in name or name in {".",".."}: raise BrainGitError("INVALID_REPOSITORY_NAME")
        path=self.repos/f"{name}.git"
        if path.exists(): raise BrainGitError("REPOSITORY_EXISTS")
        self._run(["init","--bare",str(path)])
        # Seed an explicit initial commit so HEAD/main and the browser are immediately usable.
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/"seed"
            self._run(["clone",str(path),str(work)])
            self._run(["checkout","-B","main"],cwd=work)
            (work/"README.md").write_text(f"Brain Git {name}\n",encoding="utf-8")
            self._run(["add","README.md"],cwd=work)
            env=dict(os.environ,GIT_AUTHOR_NAME="Brain",GIT_AUTHOR_EMAIL="brain@localhost",GIT_COMMITTER_NAME="Brain",GIT_COMMITTER_EMAIL="brain@localhost")
            p=subprocess.run(["git","commit","-m","initialize Brain Git repository"],cwd=work,text=True,capture_output=True,env=env)
            if p.returncode: raise BrainGitError(p.stderr.strip() or p.stdout.strip())
            self._run(["push","origin","HEAD:refs/heads/main"],cwd=work)
        repo_id=hashlib.sha256(name.encode()).hexdigest()[:24]
        with self._db() as c:c.execute("INSERT INTO repositories VALUES(?,?,?,?,?)",(repo_id,name,str(path),int(private),time.time()))
        self._audit("repository.create",name,{"private":bool(private)})
        return self.repository(name)
    def repository(self,name):
        with self._db() as c:r=c.execute("SELECT * FROM repositories WHERE name=?",(name,)).fetchone()
        if not r: raise BrainGitError("REPOSITORY_NOT_FOUND")
        return dict(r)
    def list_repositories(self):
        with self._db() as c:return [dict(x) for x in c.execute("SELECT * FROM repositories ORDER BY created_at DESC")]
    def _path(self,name): return Path(self.repository(name)["path"])
    def create_branch(self,name,branch,from_ref=""): 
        repo=self._path(name); base=from_ref.strip() or ""
        args=["branch",branch]
        if base: args.append(base)
        self._run(args,cwd=repo); self._audit("branch.create",name,{"branch":branch,"from":base or "HEAD"}); return self.branches(name)
    def commit_files(self,name,files,message,branch="main",author_name="Brain",author_email="brain@localhost"):
        repo=self._path(name)
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/"work"; self._run(["clone",str(repo),str(work)])
            if branch:
                remote_ref=self._run(["rev-parse","--verify",f"refs/remotes/origin/{branch}"],cwd=work) if self._run(["rev-parse","--verify","HEAD"],cwd=work) else ""
                if remote_ref:
                    self._run(["checkout","-B",branch,f"origin/{branch}"],cwd=work)
                else:
                    self._run(["checkout","-B",branch],cwd=work)
            for rel,content in files.items():
                p=work/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8")
            self._run(["add","--all"],cwd=work)
            env=dict(os.environ, GIT_AUTHOR_NAME=author_name,GIT_AUTHOR_EMAIL=author_email,GIT_COMMITTER_NAME=author_name,GIT_COMMITTER_EMAIL=author_email)
            p=subprocess.run(["git","commit","-m",message],cwd=work,text=True,capture_output=True,env=env)
            if p.returncode and "nothing to commit" not in p.stdout+p.stderr: raise BrainGitError(p.stderr.strip())
            sha=self._run(["rev-parse","HEAD"],cwd=work)
            self._run(["push","origin",f"HEAD:refs/heads/{branch}"],cwd=work)
        self._audit("commit.create",name,{"branch":branch,"sha":sha,"files":sorted(files),"message":message})
        return {"sha":sha,"branch":branch,"files":sorted(files)}
    def read_file_at(self,name,path,ref="HEAD"):
        data=self._run(["show",f"{ref}:{path}"],cwd=self._path(name)); return data

    def branches(self,name):
        out=self._run(["for-each-ref","--format=%(refname:short) %(objectname)","refs/heads"],cwd=self._path(name))
        return [{"name":x.split()[0],"sha":x.split()[1]} for x in out.splitlines() if x.strip()]
    def refs(self,name):
        return self._run(["show-ref"],cwd=self._path(name)) if self._run(["show-ref"],cwd=self._path(name),input=None) else ""
    def fsck(self,name):
        p=subprocess.run(["git","fsck","--full","--strict"],cwd=self._path(name),text=True,capture_output=True)
        return {"ok":p.returncode==0,"stdout":p.stdout,"stderr":p.stderr}
    def audit(self,name=None):
        q="SELECT * FROM audit"; args=()
        if name:q+=" WHERE repository=?";args=(name,)
        q+=" ORDER BY id"
        with self._db() as c:return [dict(x) for x in c.execute(q,args)]
    def clone_url(self,name,host="127.0.0.1",port=8012):
        return f"http://{host}:{port}/git/{name}.git"
