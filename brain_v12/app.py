# V14 HUMAN-READABLE UI INTEGRATION
import os
import ast
import base64
import json
import pathlib
import threading
import subprocess
import httpx
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, Response, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .brain.memory import MemoryStore
from .brain.core import BrainCore
from .brain.agent import Agent
from .brain.builder import SoftwareBuilder
from .brain.orchestrator import CognitiveOrchestrator
from .brain.capabilities import CAPABILITIES, PLUGINS, TOOLS
from .brain.self_improvement import SelfImprovementEngine
from .brain.cognitive_loop import CognitiveLoop
from .brain.ai_gateway import AIGateway
from .brain.openai_provider import OpenAIProvider
from .brain.plugin_manager import PluginManager
from brain_v7.braincore_v2.code_workspace_tool import CodeWorkspaceTool, CodeChange
from brain_v7.braincore_v2.code_tool_engineering_team import CodeToolEngineeringTeam
from brain_v7.braincore_v2.code_tool_api import CodeTool
from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy
from .brain.code_agent import BrainCodeAgent
from .brain.secret_control import SecretControlPlane
from .brain.control_auth import require_control_key
from .brain.workforce_control import WorkforceControl
from .brain.income_strategy import IncomeStrategy
from .brain.live_opportunity_researcher import LiveOpportunityResearcher
from .brain.income_lifecycle import IncomeLifecycle
from .brain.problem_solver import ProblemSolver
from .brain.device_bridge import DeviceBridge
from .brain.mining_engine import MiningEngine
from .brain.freelance_agent import FreelanceAgent
from .brain.youtube_oauth import YouTubeOAuth
from .movie_summary_factory.engine import create_job, mark_stage
from .movie_summary_factory.cinematic_v3 import build_v3_plan, validate_v3
from . import media_engine
from . import visual_engine

ROOT=os.path.dirname(__file__)
store=MemoryStore(os.getenv("BRAIN_DB",os.path.join(ROOT,"brain_v12.db"))); store.init()
brain=BrainCore(store); agent=Agent(); builder=SoftwareBuilder()
orchestrator=CognitiveOrchestrator(store,brain,builder); self_improver=SelfImprovementEngine()
cognitive=CognitiveLoop(store); ai=AIGateway(); openai_provider=OpenAIProvider(); plugins=PluginManager()
code_root=os.getenv("BRAIN_CODE_ROOT", os.path.abspath(os.path.join(ROOT, "..")))
code_workspace=CodeWorkspaceTool(root=code_root, allowed_prefixes=("brain_v7/","brain_v12/"))
code_team=CodeToolEngineeringTeam(EmployeeHierarchy(), code_workspace)
code_tool=CodeTool(code_workspace, code_team)
brain_code_agent=BrainCodeAgent(openai_provider, code_tool, code_workspace)
cognitive.code_tool=code_tool

secret_control=SecretControlPlane()
workforce=WorkforceControl(store)
mining=MiningEngine()
freelance=FreelanceAgent(store)
youtube_oauth=YouTubeOAuth(store)
income_strategy=IncomeStrategy(workforce.income_engine)
live_income_researcher=LiveOpportunityResearcher(workforce.income_engine, store)
income_lifecycle=IncomeLifecycle(store)
problem_solver=ProblemSolver(cognitive)
device_bridge=DeviceBridge(store)
cognitive.device_bridge=device_bridge
if device_bridge.configured():
    cognitive.permissions.grant("device_agent")
try:
    store.purge_non_live_income_opportunities()
except Exception as exc:
    store.event("INCOME_LEGACY_PURGE_FAILED", {"error": str(exc)[:1000]})
workforce.dispatch("startup")
for p in PLUGINS:
    plugin_id=p.get("id") if isinstance(p,dict) else str(p)
    plugin_name=p.get("name",plugin_id) if isinstance(p,dict) else str(p)
    plugin_permission=p.get("permission") if isinstance(p,dict) else None
    registered=plugins.register(plugin_id,plugin_name,"1.0",[],[plugin_permission] if plugin_permission else [])
    if isinstance(p,dict) and p.get("enabled"):
        plugins.enable(plugin_id)

APP_VERSION=os.getenv("BRAIN_V14_VERSION","14.0")
DEPLOY_COMMIT=os.getenv("GITHUB_SHA") or os.getenv("GIT_COMMIT") or "unknown"
DEPLOY_BRANCH=os.getenv("GITHUB_REF_NAME","unknown")
DEPLOY_REPOSITORY=os.getenv("GITHUB_REPOSITORY","unknown")
DEPLOY_SERVICE_ID=os.getenv("GITHUB_RUN_ID","unknown")
RUNTIME_INSTANCE=os.getenv("HOSTNAME") or os.getenv("HOSTNAME") or "unknown"
app=FastAPI(title="Electronic Brain V14",version=APP_VERSION)

@app.middleware("http")
async def no_cache(request, call_next):
    response=await call_next(request)
    response.headers["Cache-Control"]="no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"]="no-cache"
    return response

class BrainHubRepoIn(BaseModel):
    owner:str=""
    repo:str=""
    branch:str="main"

class BrainHubCreateRepoIn(BaseModel):
    name:str
    description:str=""
    private:bool=False

class BrainHubFileIn(BaseModel):
    path:str
    content:str=""
    message:str="brain: update file"
    branch:str="main"
    sha:str=""

class QuickEditorReadIn(BaseModel):
    path:str
    branch:str="main"

class QuickEditorValidateIn(BaseModel):
    path:str
    content:str

class QuickEditorWriteIn(BaseModel):
    path:str
    content:str
    branch:str="main"
    commit_message:str="brain: quick editor update"
    expected_sha:str=""
    run_tests:bool=True

def _quick_editor_path(path:str)->str:
    raw=path.strip().replace("\\","/")
    if not raw or raw.startswith("/") or ".." in pathlib.PurePosixPath(raw).parts:
        raise HTTPException(status_code=400, detail="INVALID_PATH")
    if not raw.startswith(("brain_v12/","brain_v7/","cloud/","docs/","cinematic_image_engine_v51/","brain_emulator/","brain_emulator_agent/")):
        raise HTTPException(status_code=403, detail="PATH_NOT_ALLOWED")
    return raw

def _quick_editor_validate(path:str, content:str):
    path=_quick_editor_path(path)
    ext=pathlib.PurePosixPath(path).suffix.lower()
    errors=[]; warnings=[]
    if len(content.encode("utf-8")) > 1024*1024: errors.append("FILE_TOO_LARGE")
    if ext==".py":
        try: ast.parse(content, filename=path)
        except SyntaxError as exc: errors.append(f"PYTHON_SYNTAX:{exc.msg}:line={exc.lineno}:col={exc.offset}")
    elif ext==".json":
        try: json.loads(content)
        except json.JSONDecodeError as exc: errors.append(f"JSON_SYNTAX:{exc.msg}:line={exc.lineno}:col={exc.colno}")
    elif ext in {".yml",".yaml"} and "\t" in content: errors.append("YAML_TABS_NOT_ALLOWED")
    elif ext in {".html",".js",".css"} and not content.strip(): warnings.append("EMPTY_FILE")
    if "RENDER" in content.upper(): warnings.append("LEGACY_RENDER_REFERENCE")
    return {"ok":not errors,"path":path,"extension":ext,"errors":errors,"warnings":warnings}

def _github_config():
    return {"configured":bool(os.getenv("BRAIN_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")),
            "repository":os.getenv("BRAIN_GITHUB_REPOSITORY") or os.getenv("GITHUB_REPOSITORY") or "omarenserat1980/MySimpleProject",
            "branch":os.getenv("BRAIN_GITHUB_BRANCH") or os.getenv("GITHUB_REF_NAME") or "main"}

def _github_headers():
    token=os.getenv("BRAIN_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token: raise HTTPException(status_code=503,detail="GITHUB_TOKEN_NOT_CONFIGURED")
    return {"Accept":"application/vnd.github+json","Authorization":f"Bearer {token}","X-GitHub-Api-Version":"2026-03-10"}

def _github_repo():
    repo=os.getenv("BRAIN_GITHUB_REPOSITORY") or os.getenv("GITHUB_REPOSITORY") or "omarenserat1980/MySimpleProject"
    if "/" not in repo: raise HTTPException(status_code=500,detail="INVALID_GITHUB_REPOSITORY")
    return repo

@app.get("/api/brain-hub/config")
def brain_hub_config():
    cfg=_github_config()
    return {"ok":True,"name":"BRAIN Code Hub","github":cfg,
            "features":["repositories","files","commits","branches","issues","pull_requests","actions"]}

@app.get("/api/brain-hub/repositories")
async def brain_hub_repositories():
    repo=_github_repo()
    owner,name=repo.split("/",1)
    url=f"https://api.github.com/users/{owner}/repos"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r=await client.get(url,headers=_github_headers(),params={"per_page":100,"sort":"updated"})
        if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:1000])
        return {"ok":True,"repositories":[{"name":x["name"],"full_name":x["full_name"],"private":x["private"],"default_branch":x.get("default_branch","main"),"description":x.get("description") or "","html_url":x.get("html_url")} for x in r.json()]}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502,detail=f"GITHUB_NETWORK_ERROR:{exc}")

@app.get("/api/brain-hub/repository")
async def brain_hub_repository(owner:str="",repo:str="",branch:str="main"):
    full=owner and f"{owner}/{repo}" or _github_repo()
    url=f"https://api.github.com/repos/{full}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r=await client.get(url,headers=_github_headers())
        if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:1000])
        x=r.json()
        return {"ok":True,"repository":{"full_name":x["full_name"],"name":x["name"],"owner":x["owner"]["login"],"default_branch":x.get("default_branch",branch),"private":x["private"],"description":x.get("description") or "","html_url":x.get("html_url"),"updated_at":x.get("updated_at")}}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502,detail=f"GITHUB_NETWORK_ERROR:{exc}")

@app.get("/api/brain-hub/tree")
async def brain_hub_tree(path:str="",branch:str="main",owner:str="",repo:str=""):
    full=owner and f"{owner}/{repo}" or _github_repo()
    url=f"https://api.github.com/repos/{full}/contents/{path}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r=await client.get(url,headers=_github_headers(),params={"ref":branch})
        if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:1000])
        return {"ok":True,"items":[{"name":x["name"],"path":x["path"],"type":x["type"],"sha":x.get("sha"),"size":x.get("size",0),"download_url":x.get("download_url")} for x in r.json()]}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502,detail=f"GITHUB_NETWORK_ERROR:{exc}")

@app.get("/api/brain-hub/file")
async def brain_hub_file(path:str,branch:str="main",owner:str="",repo:str=""):
    full=owner and f"{owner}/{repo}" or _github_repo()
    url=f"https://api.github.com/repos/{full}/contents/{path}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r=await client.get(url,headers=_github_headers(),params={"ref":branch})
        if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:1000])
        x=r.json(); raw=x.get("content","")
        content=base64.b64decode(raw.replace("\n","")).decode("utf-8") if raw else ""
        return {"ok":True,"path":path,"branch":branch,"sha":x.get("sha"),"content":content,"html_url":x.get("html_url")}
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(status_code=502,detail=f"GITHUB_FILE_ERROR:{exc}")

@app.get("/api/brain-hub/commits")
async def brain_hub_commits(owner:str="",repo:str="",branch:str="main",per_page:int=30):
    full=owner and f"{owner}/{repo}" or _github_repo()
    url=f"https://api.github.com/repos/{full}/commits"
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(url,headers=_github_headers(),params={"sha":branch,"per_page":min(max(per_page,1),100)})
    if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:1000])
    return {"ok":True,"commits":[{"sha":x["sha"],"message":x["commit"]["message"].splitlines()[0],"author":(x["author"] or {}).get("login") or x["commit"]["author"].get("name"),"date":x["commit"]["author"].get("date"),"html_url":x.get("html_url")} for x in r.json()]}

@app.get("/api/brain-hub/branches")
async def brain_hub_branches(owner:str="",repo:str=""):
    full=owner and f"{owner}/{repo}" or _github_repo()
    url=f"https://api.github.com/repos/{full}/branches"
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(url,headers=_github_headers(),params={"per_page":100})
    if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:1000])
    return {"ok":True,"branches":[{"name":x["name"],"protected":bool(x.get("protected")),"sha":x["commit"]["sha"]} for x in r.json()]}

@app.get("/api/brain-hub/issues")
async def brain_hub_issues(owner:str="",repo:str="",state:str="open"):
    full=owner and f"{owner}/{repo}" or _github_repo()
    url=f"https://api.github.com/repos/{full}/issues"
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(url,headers=_github_headers(),params={"state":state,"per_page":100})
    if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:1000])
    return {"ok":True,"issues":[{"number":x["number"],"title":x["title"],"state":x["state"],"labels":[l["name"] for l in x.get("labels",[])],"user":(x.get("user") or {}).get("login"),"html_url":x.get("html_url"),"pull_request":bool(x.get("pull_request"))} for x in r.json()]}

@app.get("/api/brain-hub/actions")
async def brain_hub_actions(owner:str="",repo:str="",per_page:int=20):
    full=owner and f"{owner}/{repo}" or _github_repo()
    url=f"https://api.github.com/repos/{full}/actions/runs"
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(url,headers=_github_headers(),params={"per_page":min(max(per_page,1),100)})
    if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:1000])
    return {"ok":True,"runs":[{"id":x["id"],"name":x["name"],"status":x["status"],"conclusion":x["conclusion"],"branch":x.get("head_branch"),"sha":x.get("head_sha"),"html_url":x.get("html_url"),"created_at":x.get("created_at")} for x in r.json()]}


class BrainHubCreateBranchIn(BaseModel):
    owner:str=""
    repo:str=""
    name:str
    from_ref:str="main"

class BrainHubIssueIn(BaseModel):
    owner:str=""
    repo:str=""
    title:str
    body:str=""
    labels:list[str]=[]

class BrainHubPullIn(BaseModel):
    owner:str=""
    repo:str=""
    title:str
    head:str
    base:str="main"
    body:str=""

class BrainHubActionIn(BaseModel):
    owner:str=""
    repo:str=""

class BrainHubCreateRepoIn(BaseModel):
    name:str
    description:str=""
    private:bool=False
    auto_init:bool=True

def _brain_hub_full(owner:str="", repo:str=""):
    full = f"{owner.strip()}/{repo.strip()}" if owner.strip() and repo.strip() else _github_repo()
    if "/" not in full or any(part.strip() == "" for part in full.split("/",1)):
        raise HTTPException(status_code=400, detail="INVALID_GITHUB_REPOSITORY")
    return full

@app.post("/api/brain-hub/repositories")
async def brain_hub_create_repository(body:BrainHubCreateRepoIn):
    name=body.name.strip()
    if not name or "/" in name or len(name)>100:
        raise HTTPException(status_code=400, detail="INVALID_REPOSITORY_NAME")
    payload={"name":name,"description":body.description.strip(),"private":body.private,"auto_init":body.auto_init}
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post("https://api.github.com/user/repos",headers=_github_headers(),json=payload)
    if r.status_code>=400:
        raise HTTPException(status_code=r.status_code,detail=r.text[:2000])
    x=r.json()
    return {"ok":True,"repository":{"full_name":x.get("full_name"),"name":x.get("name"),"default_branch":x.get("default_branch","main"),"private":x.get("private"),"html_url":x.get("html_url")}}

@app.post("/api/brain-hub/branches")
async def brain_hub_create_branch(body:BrainHubCreateBranchIn):
    full=_brain_hub_full(body.owner,body.repo)
    name=body.name.strip().replace(" ","-")
    if not name or name in {"main","master"}:
        raise HTTPException(status_code=400,detail="INVALID_BRANCH_NAME")
    base=body.from_ref.strip() or "main"
    async with httpx.AsyncClient(timeout=30) as client:
        ref=await client.get(f"https://api.github.com/repos/{full}/git/ref/heads/{base}",headers=_github_headers())
        if ref.status_code>=400:
            raise HTTPException(status_code=ref.status_code,detail=ref.text[:1000])
        sha=ref.json().get("object",{}).get("sha")
        r=await client.post(f"https://api.github.com/repos/{full}/git/refs",headers=_github_headers(),json={"ref":f"refs/heads/{name}","sha":sha})
    if r.status_code>=400:
        raise HTTPException(status_code=r.status_code,detail=r.text[:2000])
    return {"ok":True,"branch":name,"sha":sha,"from_ref":base}

@app.post("/api/brain-hub/issues")
async def brain_hub_create_issue(body:BrainHubIssueIn):
    full=_brain_hub_full(body.owner,body.repo)
    payload={"title":body.title.strip(),"body":body.body}
    if body.labels: payload["labels"]=body.labels
    if not payload["title"]: raise HTTPException(status_code=400,detail="ISSUE_TITLE_REQUIRED")
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(f"https://api.github.com/repos/{full}/issues",headers=_github_headers(),json=payload)
    if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:2000])
    x=r.json()
    return {"ok":True,"issue":{"number":x.get("number"),"title":x.get("title"),"state":x.get("state"),"html_url":x.get("html_url")}}

@app.post("/api/brain-hub/pulls")
async def brain_hub_create_pull(body:BrainHubPullIn):
    full=_brain_hub_full(body.owner,body.repo)
    if not body.title.strip() or not body.head.strip() or not body.base.strip():
        raise HTTPException(status_code=400,detail="PULL_REQUEST_FIELDS_REQUIRED")
    payload={"title":body.title.strip(),"head":body.head.strip(),"base":body.base.strip(),"body":body.body}
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(f"https://api.github.com/repos/{full}/pulls",headers=_github_headers(),json=payload)
    if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:2000])
    x=r.json()
    return {"ok":True,"pull":{"number":x.get("number"),"title":x.get("title"),"state":x.get("state"),"draft":x.get("draft"),"html_url":x.get("html_url")}}

@app.post("/api/brain-hub/actions/{run_id}/cancel")
async def brain_hub_cancel_action(run_id:int, body:BrainHubActionIn):
    full=_brain_hub_full(body.owner,body.repo)
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(f"https://api.github.com/repos/{full}/actions/runs/{run_id}/cancel",headers=_github_headers())
    if r.status_code not in (202,204):
        raise HTTPException(status_code=r.status_code,detail=r.text[:2000])
    return {"ok":True,"run_id":run_id,"status":"CANCEL_REQUESTED"}

@app.post("/api/brain-hub/actions/{run_id}/rerun")
async def brain_hub_rerun_action(run_id:int, body:BrainHubActionIn):
    full=_brain_hub_full(body.owner,body.repo)
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(f"https://api.github.com/repos/{full}/actions/runs/{run_id}/rerun-failed-jobs",headers=_github_headers())
    if r.status_code not in (201,202,204):
        raise HTTPException(status_code=r.status_code,detail=r.text[:2000])
    return {"ok":True,"run_id":run_id,"status":"RERUN_REQUESTED"}

@app.get("/api/brain-hub/pulls")
async def brain_hub_pulls(owner:str="",repo:str="",state:str="open"):
    full=_brain_hub_full(owner,repo)
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(f"https://api.github.com/repos/{full}/pulls",headers=_github_headers(),params={"state":state,"per_page":100})
    if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:1000])
    return {"ok":True,"pulls":[{"number":x["number"],"title":x["title"],"state":x["state"],"draft":x.get("draft",False),"head":(x.get("head") or {}).get("ref"),"base":(x.get("base") or {}).get("ref"),"html_url":x.get("html_url")} for x in r.json()]}

@app.get("/api/brain-hub/compare")
async def brain_hub_compare(owner:str="",repo:str="",base:str="main",head:str="main"):
    full=_brain_hub_full(owner,repo)
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(f"https://api.github.com/repos/{full}/compare/{base}...{head}",headers=_github_headers())
    if r.status_code>=400: raise HTTPException(status_code=r.status_code,detail=r.text[:2000])
    x=r.json()
    return {"ok":True,"status":x.get("status"),"ahead_by":x.get("ahead_by"),"behind_by":x.get("behind_by"),"total_commits":x.get("total_commits"),"files":[{"filename":f.get("filename"),"status":f.get("status"),"additions":f.get("additions"),"deletions":f.get("deletions"),"changes":f.get("changes")} for f in x.get("files",[])],"html_url":x.get("html_url")}

@app.get("/api/quick-editor/status")
def quick_editor_status():
    return {"ok":True,"editor":"BRAIN Quick Editor","runtime":"BRAIN_TERMUX_EMULATOR","github":_github_config(),
            "features":["read","validate","preview","checkpoint","github_write","tests"]}

@app.post("/api/quick-editor/validate")
def quick_editor_validate(body:QuickEditorValidateIn):
    return _quick_editor_validate(body.path,body.content)

@app.get("/api/quick-editor/read")
async def quick_editor_read(path:str,branch:str="main"):
    path=_quick_editor_path(path); repo=_github_repo()
    url=f"https://api.github.com/repos/{repo}/contents/{path}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r=await client.get(url,headers=_github_headers(),params={"ref":branch})
        if r.status_code==404: raise HTTPException(status_code=404,detail="FILE_NOT_FOUND")
        if r.status_code>=400: return {"ok":False,"status_code":r.status_code,"detail":r.text[:1000]}
        data=r.json(); raw=data.get("content","")
        content=base64.b64decode(raw.replace("\n","")).decode("utf-8") if raw else ""
        return {"ok":True,"path":path,"branch":branch,"sha":data.get("sha"),"content":content}
    except httpx.HTTPError as exc:
        return {"ok":False,"error":"GITHUB_NETWORK_ERROR","detail":str(exc)[:1000]}

@app.post("/api/quick-editor/write")
async def quick_editor_write(request:Request,body:QuickEditorWriteIn):
    require_control_key(request)
    path=_quick_editor_path(body.path); validation=_quick_editor_validate(path,body.content)
    if not validation["ok"]: return {"ok":False,"status":"VALIDATION_FAILED","validation":validation}
    repo=_github_repo(); branch=body.branch.strip() or "main"; url=f"https://api.github.com/repos/{repo}/contents/{path}"; headers=_github_headers()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            current=await client.get(url,headers=headers,params={"ref":branch})
            current_data=current.json() if current.status_code==200 else {}; current_sha=current_data.get("sha")
            if body.expected_sha and current_sha and body.expected_sha!=current_sha:
                return {"ok":False,"status":"CONFLICT","expected_sha":body.expected_sha,"actual_sha":current_sha}
            payload={"message":body.commit_message.strip() or "brain: quick editor update",
                     "content":base64.b64encode(body.content.encode("utf-8")).decode("ascii"),"branch":branch}
            if current_sha: payload["sha"]=current_sha
            result=await client.put(url,headers=headers,json=payload)
        if result.status_code not in (200,201):
            return {"ok":False,"status":"GITHUB_WRITE_FAILED","status_code":result.status_code,"detail":result.text[:2000]}
        data=result.json(); commit_sha=data.get("commit",{}).get("sha")
        store.event("QUICK_EDITOR_GITHUB_WRITE",{"path":path,"branch":branch,"commit":commit_sha,"validation":"PASS"})
        return {"ok":True,"status":"COMMITTED","path":path,"branch":branch,"sha":data.get("content",{}).get("sha"),"commit_sha":commit_sha,
                "validation":validation,"tests":{"status":"QUEUED","note":"GitHub Actions will verify the commit."} if body.run_tests else None}
    except httpx.HTTPError as exc:
        return {"ok":False,"status":"GITHUB_NETWORK_ERROR","detail":str(exc)[:1000]}

class BrainCodePlanIn(BaseModel):
    objective:str
    files:list[str]=[]

class BrainCodeApplyIn(BaseModel):
    objective:str
    files:list[str]=[]
    approved:bool=False
    commit_message:str="brain: validated self-improvement"
    persist_to_github:bool=True

class Chat(BaseModel): message:str
class Goal(BaseModel): text:str; priority:float=0.5
class Memory(BaseModel): key:str; value:str
class Observe(BaseModel): actual:str
class Learn(BaseModel): lesson:str
class Exec(BaseModel): command:list[str]; cwd:str="."; timeout:int=30; approved:bool=False
class Improve(BaseModel): objective:str; files:list[str]=[]
class Permission(BaseModel): capability:str
class CodeChangeIn(BaseModel): path:str; content:str; reason:str=""
class CodeChanges(BaseModel):
    changes:list[CodeChangeIn]
    reason:str=""
    commit_message:str="brain: controlled code change"
    approved:bool=False
    persist_to_github:bool=True
class CodePaths(BaseModel): paths:list[str]=[]

class MediaJobIn(BaseModel):
    operation: str
    spec: dict = {}

class VisualCompileIn(BaseModel):
    prompt: str
    mode: str = "auto"

@app.post("/api/visual-engine/compile")
def visual_engine_compile(body: VisualCompileIn):
    scene = visual_engine.compile_scene(body.prompt, body.mode)
    return {"ok": True, "scene": scene, "svg": visual_engine.render_svg(scene)}

@app.get("/api/visual-engine/health")
def visual_engine_health():
    return {"ok": True, "engine": "BRAIN Visual Engine", "renderer": "SVG", "local": True, "external_api": False}


@app.get("/api/media/health")
def media_health():
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    return {
        "ok": bool(ffmpeg and ffprobe),
        "engine": "BRAIN Media Engine",
        "version": "1.0",
        "ffmpeg": bool(ffmpeg),
        "ffprobe": bool(ffprobe),
        "media_root": str(media_engine.MEDIA_ROOT),
        "queue_workers": media_engine.MAX_WORKERS,
        "operations": ["probe", "convert", "concat", "extract-audio", "extract-frames", "slideshow", "trim", "mix-audio", "fade", "timeline"],
    }


@app.post("/api/media/jobs")
def media_create_job(body: MediaJobIn):
    try:
        job = media_engine.submit(body.operation.strip().lower(), body.spec)
        store.event("MEDIA_JOB_CREATED", {"job_id": job["job_id"], "operation": body.operation})
        return job
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/media/jobs")
def media_jobs(limit: int = 30):
    return {"ok": True, "jobs": media_engine.list_jobs(limit)}


@app.get("/api/media/jobs/{job_id}")
def media_job(job_id: str):
    return media_engine.snapshot(job_id)

@app.post("/api/media/jobs/{job_id}/cancel")
def media_cancel_job(job_id: str):
    return media_engine.cancel(job_id)



@app.post("/api/media/probe")
def media_probe(body: MediaJobIn):
    try:
        return media_engine.submit("probe", {"input": body.spec.get("input", "")})
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/convert")
def media_convert(body: MediaJobIn):
    try:
        return media_engine.submit("convert", body.spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/concat")
def media_concat(body: MediaJobIn):
    try:
        return media_engine.submit("concat", body.spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/extract-audio")
def media_extract_audio(body: MediaJobIn):
    try:
        return media_engine.submit("extract-audio", body.spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/extract-frames")
def media_extract_frames(body: MediaJobIn):
    try:
        return media_engine.submit("extract-frames", body.spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/trim")
def media_trim(body: MediaJobIn):
    try:
        return media_engine.submit("trim", body.spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/mix-audio")
def media_mix_audio(body: MediaJobIn):
    try:
        return media_engine.submit("mix-audio", body.spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/fade")
def media_fade(body: MediaJobIn):
    try:
        return media_engine.submit("fade", body.spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/media/presets")
def media_presets():
    return {
        "ok": True,
        "presets": {
            "youtube_1080p": {"width": 1920, "height": 1080, "fps": 30, "crf": 20},
            "shorts_1080x1920": {"width": 1080, "height": 1920, "fps": 30, "crf": 20},
            "cinematic_4k": {"width": 3840, "height": 2160, "fps": 24, "crf": 20},
        },
        "transitions": ["none", "fade", "wipeleft", "wiperight", "slideleft", "slideright"],
    }


@app.post("/api/media/cinematic-render")
def media_cinematic_render(body: MediaJobIn):
    try:
        spec = dict(body.spec)
        spec.setdefault("profile", "youtube_1080p")
        return media_engine.submit("timeline", spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/timeline")
def media_timeline(body: MediaJobIn):
    try:
        return media_engine.submit("timeline", body.spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/visual-scene")
def media_visual_scene(body: MediaJobIn):
    """Render a deterministic Visual Engine scene into a media asset and optionally build an MP4."""
    try:
        spec = dict(body.spec or {})
        scene = spec.get("scene")
        if not isinstance(scene, dict):
            prompt = str(spec.get("prompt") or "منظر طبيعي")
            scene = visual_engine.compile_scene(prompt, str(spec.get("mode") or "auto"))
        svg = visual_engine.render_svg(scene)
        filename = media_engine._safe_name(str(spec.get("filename") or "brain-visual-scene.svg"))
        if not filename.lower().endswith(".svg"):
            filename += ".svg"
        target = (media_engine.MEDIA_ROOT / filename).resolve()
        if media_engine.MEDIA_ROOT not in target.parents:
            raise ValueError("MEDIA_PATH_OUTSIDE_WORKSPACE")
        target.write_text(svg, encoding="utf-8")
        result = {"ok": True, "scene": scene, "svg": f"/media/{filename}", "filename": filename}
        if bool(spec.get("render_mp4")):
            duration = max(0.5, min(float(spec.get("duration") or 5), 120))
            image_name = filename
            # SVG is retained as the canonical editable asset; convert through the existing
            # allowlisted slideshow operation only after a raster asset is supplied.
            result["next_step"] = "RASTER_ASSET_REQUIRED"
            result["duration"] = duration
            result["timeline"] = visual_engine.scene_timeline(scene, duration)
        return result
    except (ValueError, OSError, TypeError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/media/slideshow")
def media_slideshow(body: MediaJobIn):
    try:
        return media_engine.submit("slideshow", body.spec)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class CinematicReleaseIn(BaseModel):
    title: str
    description: str = ""
    media_path: str = ""
    tags: list[str] = []
    privacy: str = "private"

@app.post("/api/media/upload")
async def media_upload(file:UploadFile=File(...)):
    media_dir=os.path.join(ROOT,"web","media"); os.makedirs(media_dir,exist_ok=True)
    safe=os.path.basename(file.filename or "upload.bin"); target=os.path.join(media_dir,safe); data=await file.read()
    if len(data) > 20 * 1024 * 1024:
        return {"ok":False,"error":"MEDIA_TOO_LARGE","max_bytes":20 * 1024 * 1024}
    with open(target,"wb") as f: f.write(data)
    store.event("MEDIA_RECEIVED",{"filename":safe,"content_type":file.content_type,"size":len(data)})
    return {"ok":True,"filename":safe,"url":f"/media/{safe}","content_type":file.content_type,"size":len(data)}

@app.post("/api/youtube/cinematic/validate")
def youtube_cinematic_validate(body: CinematicReleaseIn, request: Request):
    require_control_key(request)
    return workforce.youtube_publisher.validate_release(body.title, body.media_path, body.description, body.tags)

@app.get("/api/youtube/oauth/status")
def youtube_oauth_status():
    return youtube_oauth.snapshot()

@app.get("/api/youtube/oauth/start")
def youtube_oauth_start():
    # OAuth start is intentionally public: it only creates a short-lived state and redirects the user to Google.
    # The callback remains state-bound and the token is stored encrypted.
    return youtube_oauth.start()

@app.get("/api/youtube/oauth/readiness")
def youtube_oauth_readiness():
    snapshot = youtube_oauth.snapshot()
    return {
        "ok": True,
        "configured": snapshot.get("configured", False),
        "ready_to_start": snapshot.get("ready_to_start", False),
        "ready_to_store_token": snapshot.get("ready_to_store_token", False),
        "authorized": snapshot.get("authorized", False),
        "next_step": (
            "AUTHORIZED" if snapshot.get("authorized")
            else "AUTHORIZE_GOOGLE" if snapshot.get("ready_to_start")
            else "CONFIGURE_GITHUB_OAUTH_SECRETS"
        ),
        "scope": snapshot.get("scope", "youtube.upload"),
        "credentials_in_logs": False,
        "missing_env": snapshot.get("missing_env", []),
    }

@app.get("/api/youtube/oauth/callback")
def youtube_oauth_callback(code: str = "", state: str = ""):
    return youtube_oauth.callback(code, state)

@app.get("/api/youtube/status")
def youtube_status():
    return workforce.youtube_publisher.snapshot()

@app.post("/api/youtube/cinematic/prepare")
def youtube_cinematic_prepare(body: CinematicReleaseIn, request: Request):
    require_control_key(request)
    return workforce.prepare_cinematic_release(body.title, body.description, body.media_path, body.tags, body.privacy)

@app.post("/api/youtube/release/authorize")
def youtube_release_authorize(body: dict, request: Request):
    require_control_key(request)
    return workforce.youtube_publisher.authorize(str(body.get("release_id", "")))

@app.post("/api/youtube/release/record-published")
def youtube_release_record_published(body: dict, request: Request):
    require_control_key(request)
    return workforce.youtube_publisher.record_published(
        str(body.get("release_id", "")),
        str(body.get("published_url", "")),
        str(body.get("evidence", "")),
    )


class MovieSummaryIn(BaseModel):
    title: str
    target_minutes: int = 12
    language: str = "ar"

@app.post("/api/movie-summary/jobs")
def movie_summary_create(body: MovieSummaryIn):
    job = create_job(body.title, body.target_minutes, body.language)
    store.event("MOVIE_SUMMARY_JOB_CREATED", job)
    return {"ok": True, "job": job}

@app.post("/api/movie-summary/jobs/{job_id}/stage")
def movie_summary_stage(job_id: str, stage: str, status: str = "COMPLETED"):
    # Stage updates are recorded as Brain events so the existing cognitive/event UI can observe them.
    payload = {"job_id": job_id, "stage": stage, "status": status}
    store.event("MOVIE_SUMMARY_STAGE", payload)
    return {"ok": True, **payload}

@app.post("/api/movie-summary/v3/plan")
def movie_summary_v3_plan(body: MovieSummaryIn):
    plan = build_v3_plan(body.title, body.language, body.target_minutes)
    qc = validate_v3(plan)
    store.event("MOVIE_SUMMARY_V3_PLAN", {"title": body.title, "qc": qc})
    return {"ok": qc["status"] == "PASS", "plan": plan, "qc": qc}

@app.get("/api/movie-summary/status")
def movie_summary_status():
    events = [e for e in store.events(200) if e.get("type") in ("MOVIE_SUMMARY_JOB_CREATED", "MOVIE_SUMMARY_STAGE")]
    return {"ok": True, "jobs": events}

@app.get("/api/capabilities")
def capabilities(): return {"capabilities":CAPABILITIES,"plugins":PLUGINS,"tools":TOOLS}
@app.get("/api/mining/status")
def mining_status():
    """Return mining capability state without claiming live profitability."""
    return mining.snapshot()

@app.post("/api/mining/analyze")
def mining_analyze(body:dict):
    try:
        return mining.analyze(body)
    except (TypeError, ValueError) as exc:
        return {"ok":False,"status":"INVALID_INPUT","error":str(exc)}

@app.post("/api/mining/compare")
def mining_compare(body:dict):
    try:
        candidates=body.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            return {"ok":False,"status":"INVALID_INPUT","error":"CANDIDATES_REQUIRED"}
        return mining.compare(candidates)
    except (TypeError, ValueError) as exc:
        return {"ok":False,"status":"INVALID_INPUT","error":str(exc)}

@app.get("/api/freelance/profile")
def freelance_profile():
    return freelance.profile_snapshot()

@app.get("/api/freelance/status")
def freelance_status():
    return freelance.snapshot()

@app.post("/api/freelance/analyze")
def freelance_analyze(body:dict):
    return freelance.analyze(body)

@app.post("/api/freelance/prepare-offer")
def freelance_prepare_offer(body:dict):
    return freelance.prepare_offer(body)

@app.post("/api/freelance/application-status")
def freelance_application_status(body:dict):
    return freelance.record_application(
        str(body.get("opportunity_id", "")),
        str(body.get("status", "")),
        str(body.get("evidence", "")),
    )

@app.post("/api/freelance/payment-verified")
def freelance_payment_verified(body:dict):
    return freelance.record_verified_payment(
        str(body.get("opportunity_id", "")),
        float(body.get("amount_jod", 0) or 0),
        str(body.get("evidence", "")),
    )

@app.get("/api/workforce/health")
def workforce_health():
    return workforce.health()

@app.get("/health")
def health():
    return {
        "ok": True,
        "status": "healthy",
        "version": APP_VERSION,
        "runtime": "BRAIN_TERMUX_EMULATOR",
        "deployment": _deployment_snapshot() if "_deployment_snapshot" in globals() else {"converged": False},
    }

def _deployment_snapshot():
    expected = os.getenv("GITHUB_SHA", "")
    return {
        "version": APP_VERSION,
        "commit": DEPLOY_COMMIT,
        "github_sha": expected or None,
        "branch": DEPLOY_BRANCH,
        "repository": DEPLOY_REPOSITORY,
        "run_id": DEPLOY_SERVICE_ID,
        "instance": RUNTIME_INSTANCE,
        "converged": bool(DEPLOY_COMMIT and expected and DEPLOY_COMMIT == expected),
    }

@app.get("/api/deploy/diagnostics")
def deploy_diagnostics():
    snapshot = _deployment_snapshot()
    snapshot["marker"] = os.getenv("GITHUB_RUN_ID", "unset")
    snapshot["oauth_env"] = {
        "client_id": bool(os.getenv("YOUTUBE_CLIENT_ID")),
        "client_secret": bool(os.getenv("YOUTUBE_CLIENT_SECRET")),
        "redirect_uri": bool(os.getenv("YOUTUBE_OAUTH_REDIRECT_URI")),
        "token_encryption_key": bool(os.getenv("YOUTUBE_TOKEN_ENCRYPTION_KEY")),
    }
    return {"ok": snapshot["converged"], **snapshot}

@app.get("/api/deploy/verify")
def deploy_verify():
    snapshot = _deployment_snapshot()
    return {"ok": snapshot["converged"], "actual_commit": snapshot["commit"], "github_sha": snapshot["github_sha"], "instance": snapshot["instance"]}

@app.get("/api/deploy/identity")
def deploy_identity():
    snapshot = _deployment_snapshot()
    return {"ok": snapshot["converged"], "brain": "V13", **snapshot}

@app.get("/api/system/connection")
def system_connection():
    checks = []
    def check(name, ok, detail):
        checks.append({"name":name,"ok":bool(ok),"detail":detail})
    check("server", True, "خادم العقل V12 يستجيب")
    try:
        state = store.state()
        check("memory", isinstance(state, dict), "الذاكرة قابلة للقراءة")
    except Exception as exc:
        check("memory", False, "تعذر قراءة الذاكرة: " + str(exc)[:180])
    try:
        tool_count = len(cognitive.tool_catalog())
        check("tools", tool_count >= 0, f"{tool_count} أدوات متاحة")
    except Exception as exc:
        check("tools", False, "تعذر قراءة الأدوات: " + str(exc)[:180])
    online = all(x["ok"] for x in checks)
    return {
        "ok": online,
        "connected": online,
        "status": "CONNECTED" if online else "DISCONNECTED",
        "label_ar": "في اتصال" if online else "مفيش اتصال",
        "brain": "V13",
        "version": APP_VERSION,
        "checks": checks,
    }

@app.get("/api/device/agent-status/{agent_id}")
def device_agent_status_by_id(agent_id: str, request: Request):
    if not require_device_agent(request):
        return JSONResponse({"ok": False, "status": "UNAUTHORIZED"}, status_code=401)
    age = device_bridge.heartbeat_age_seconds(agent_id)
    if age is None:
        return JSONResponse({"ok": False, "status": "AGENT_NOT_FOUND", "agent_id": agent_id}, status_code=404)
    ttl = max(5, int(os.getenv("TERMUX_AGENT_TTL_SECONDS", "15")))
    return JSONResponse({"ok": True, "agent_id": agent_id, "age_seconds": round(age, 2), "ttl_seconds": ttl, "online": age <= ttl, "state": "ONLINE" if age <= ttl else "STALE"})

@app.get("/api/device/agent-status")
def device_agent_status(request: Request):
    if not require_device_agent(request):
        return JSONResponse({"ok": False, "status": "UNAUTHORIZED"}, status_code=401)
    return JSONResponse(device_bridge.agent_status())

@app.post("/api/device/requeue-stale")
def device_requeue_stale(request:Request):
    require_control_key(request)
    max_age=max(5, int(os.getenv("TERMUX_TASK_STALE_SECONDS", "120")))
    result=device_bridge.requeue_stale(max_age)
    store.event("DEVICE_STALE_TASKS_REQUEUED", result)
    return {**result, "max_age_seconds": max_age}


@app.get("/api/device/queue")
def device_queue(request: Request):
    if not require_device_agent(request):
        return JSONResponse({"ok": False, "status": "UNAUTHORIZED"}, status_code=401)
    return JSONResponse({"ok": True, "counts": device_bridge.queued_tasks()})

@app.get("/api/device/status")
def device_status():
    return device_bridge.status()


class DeviceTask(BaseModel):
    task:str
    params:dict={}


class DeviceReport(BaseModel):
    task_id:str
    agent_id:str
    ok:bool
    result:dict={}
    error:str=""


def require_device_agent(request:Request) -> None:
    supplied=request.headers.get("X-V12-Agent-Key","")
    if not device_bridge.authenticate(supplied):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="DEVICE_AGENT_AUTH_REQUIRED")


@app.post("/api/device/enqueue")
def device_enqueue(request:Request, body:DeviceTask):
    require_control_key(request)
    result=device_bridge.enqueue(body.task, body.params)
    store.event("DEVICE_TASK_QUEUED", {"task": body.task, "status": result.get("status"), "task_id": result.get("task",{}).get("task_id")})
    return result


@app.post("/api/device/heartbeat")
def device_heartbeat(request: Request):
    agent_id = request.headers.get("X-V12-Agent-Id") or "android-termux-v12"
    if not require_device_agent(request):
        raise HTTPException(status_code=401, detail="UNAUTHORIZED_AGENT")
    return device_bridge.heartbeat(agent_id)


@app.get("/api/device/poll")
def device_poll(request:Request, agent_id:str):
    require_device_agent(request)
    result=device_bridge.poll(agent_id)
    if result.get("task"):
        store.event("DEVICE_TASK_CLAIMED", {"task_id": result["task"]["task_id"], "agent_id": agent_id})
    return result


@app.post("/api/device/report")
def device_report(request:Request, body:DeviceReport):
    require_device_agent(request)
    result=device_bridge.report(body.task_id, body.agent_id, body.ok, body.result, body.error)
    store.event("DEVICE_TASK_RESULT", {"task_id": body.task_id, "agent_id": body.agent_id, "ok": body.ok})
    return result

@app.get("/api/device/result/{task_id}")
def device_result(task_id:str):
    return device_bridge.result(task_id)


@app.get("/api/agent-gateway/diagnostics")
def agent_gateway_diagnostics():
    bridge=device_bridge.status()
    return {
        "ok": True,
        "brain": "V13",
        "gateway": "READY" if bridge.get("configured") else "NOT_CONFIGURED",
        "transport": "HTTPS polling",
        "authentication": "X-V12-Agent-Key",
        "agent_seen": bool(bridge.get("agents", {}).get("online")),
        "agents": bridge.get("agents", {}),
        "queues": {
            "queued": bridge.get("queued", 0),
            "pending": bridge.get("pending", 0),
            "completed": bridge.get("completed", 0),
            "failed": bridge.get("failed", 0),
        },
        "allowed_tasks": sorted(device_bridge.ALLOWED_TASKS),
    }

@app.get("/api/agent-gateway/status")
def agent_gateway_status():
    return {
        "ok": True,
        "gateway": "Brain V13 ↔ Termux",
        "configured": device_bridge.configured(),
        "transport": "HTTPS polling",
        "authentication": "X-V12-Agent-Key",
        "allowed_tasks": sorted(device_bridge.ALLOWED_TASKS),
        "bridge": device_bridge.status(),
    }

@app.post("/api/agent-gateway/task")
def agent_gateway_task(request:Request, body:DeviceTask):
    """Brain-side gateway: enqueue one allowlisted task for the authenticated Termux agent."""
    require_control_key(request)
    result = device_bridge.enqueue(body.task, body.params)
    store.event("AGENT_GATEWAY_TASK_CREATED", {
        "task_id": result.get("task", {}).get("task_id"),
        "task": body.task,
        "status": result.get("status"),
    })
    return result

@app.get("/api/agent-gateway/result/{task_id}")
def agent_gateway_result(task_id:str):
    return device_bridge.result(task_id)


@app.post("/api/agent-gateway/smoke-test")
def agent_gateway_smoke_test(request:Request):
    require_control_key(request)
    created = device_bridge.enqueue("python_version", {})
    if not created.get("ok"):
        return created
    task_id = created["task"]["task_id"]
    store.event("AGENT_GATEWAY_SMOKE_TEST_CREATED", {"task_id": task_id})
    return {
        "ok": True,
        "status": "QUEUED",
        "task_id": task_id,
        "next": [
            f"/api/agent-gateway/result/{task_id}",
            f"/api/agent-gateway/verify/{task_id}",
        ],
    }

@app.get("/api/agent-gateway/verify/{task_id}")
def agent_gateway_verify(task_id:str):
    verification = device_bridge.verify_result(task_id)
    store.event("AGENT_GATEWAY_VERIFICATION", {
        "task_id": task_id,
        "verified": verification.get("verified", False),
        "status": verification.get("status"),
    })
    return verification


@app.get("/api/system/status")
def system_status():
    state=store.state()
    return {"ok":True,"status":"ONLINE" if state.get("status")!="ERROR" else "DEGRADED","brain":"V12","version":APP_VERSION,
            "stage":state.get("cognitive_stage","READY"),"run_id":state.get("cognitive_trace",{}).get("run_id"),
            "tools":len(cognitive.tool_catalog()),"memory_items":len(store.memories()),"event_count":len(store.events(1000))}

@app.get("/api/security/secrets/status")
def security_secrets_status():
    return secret_control.status()


@app.post("/api/security/secrets/plan")
def security_secrets_plan(names:list[str]|None=None):
    return secret_control.plan(names)


@app.get("/api/monitor/incidents")
def monitor_incidents(limit:int=50):
    return {"ok":True,"incidents":store.incidents(max(1,min(limit,200)))}

@app.get("/api/income/mission")
def income_mission():
    return income_strategy.mission()

@app.get("/api/income/search-plan")
def income_search_plan():
    return income_strategy.search_plan()

@app.get("/api/income/opportunities")
def income_opportunities(limit:int=20):
    engine=workforce.income_engine
    return {"ok":True,"summary":engine.snapshot(),"items":engine.prioritize(max(1,min(limit,100))),"lifecycle":income_lifecycle.summary()}


@app.post("/api/income/discover")
def income_discover(request:Request):
    require_control_key(request)
    channels=workforce.income_engine.discover(20)
    result=live_income_researcher.run_once()
    return {"ok":result.get("ok",False),"channels_available":len(channels),"live_search":result,
            "summary":workforce.income_engine.snapshot()}

@app.post("/api/income/live-search")
def income_live_search(request:Request):
    require_control_key(request)
    return live_income_researcher.run_once()

@app.get("/api/render/monitor")
def render_monitor_status():
    return {"ok":True,"deploy_monitor":render_deploy_monitor.status(),"log_monitor":render_monitor.status()}


class IncomeLifecycleRequest(BaseModel):
    opportunity_id:str
    notes:str=""


class IncomePrepareRequest(BaseModel):
    opportunity_id:str
    proposal:str=""


class IncomeExternalEvidence(BaseModel):
    opportunity_id:str
    status:str
    evidence:str


@app.get("/api/income/lifecycle-report")
def income_lifecycle_report(limit:int=100):
    return workforce.income_engine.lifecycle_report(max(1,min(limit,500)))


@app.post("/api/income/research-run")
def income_research_run(request: Request):
    require_control_key(request)
    return workforce.live_opportunity_researcher.run_once()


@app.post("/api/income/lifecycle-refresh")
def income_lifecycle_refresh(request:Request, max_age_hours:float=72, limit:int=500):
    require_control_key(request)
    return workforce.income_engine.refresh_lifecycle(
        max_age_hours=max(1, min(float(max_age_hours), 720)),
        limit=max(1, min(int(limit), 500)),
    )


@app.get("/api/income/lifecycle")
def income_lifecycle_status():
    return {"ok":True,"lifecycle":income_lifecycle.summary()}


@app.post("/api/income/qualify")
def income_qualify(request:Request, body:IncomeLifecycleRequest):
    require_control_key(request)
    return income_lifecycle.qualify(body.opportunity_id, body.notes)


@app.post("/api/income/prepare")
def income_prepare(request:Request, body:IncomePrepareRequest):
    require_control_key(request)
    return income_lifecycle.prepare(body.opportunity_id, body.proposal)


@app.post("/api/income/external-evidence")
def income_external_evidence(request:Request, body:IncomeExternalEvidence):
    require_control_key(request)
    allowed={"SUBMITTED","CLIENT_RESPONDED","ACCEPTED","DELIVERING","COMPLETED"}
    if body.status not in allowed:
        return {"ok":False,"status":"INVALID_EXTERNAL_STATUS","allowed":sorted(allowed)}
    return income_lifecycle.record_external(body.opportunity_id, body.status, body.evidence)


class IncomeVerification(BaseModel):
    opportunity_id:str
    amount_jod:float
    evidence:str


@app.post("/api/income/verify")
def income_verify(request:Request, body:IncomeVerification):
    require_control_key(request)
    row=income_lifecycle._find(body.opportunity_id)
    if not row:
        return {"ok":False,"status":"NOT_FOUND"}
    if str(row.get("status")) not in ("COMPLETED", "PAYMENT_VERIFIED"):
        return {"ok":False,"status":"DELIVERY_NOT_VERIFIED","current":row.get("status"),
                "reason":"يجب إثبات القبول/التنفيذ/التسليم قبل تسجيل الدفع."}
    result=workforce.income_engine.verify_payment(body.opportunity_id,body.amount_jod,body.evidence)
    if result.get("ok"):
        income_lifecycle._save(row,status="PAYMENT_VERIFIED",payment_evidence=body.evidence[:4000],
                               payment_verified_at=income_lifecycle._now())
    return result


@app.get("/api/workforce/report")
def workforce_report():
    return workforce.report()

@app.post("/api/workforce/dispatch")
def workforce_dispatch(request:Request):
    require_control_key(request)
    return workforce.dispatch("manual_control_plane")

@app.get("/api/system/overview")
def system_overview():
    """Read-only, human-oriented map of the live Brain V12 architecture and operating state."""
    state = store.state()
    income = income_strategy.mission()
    workforce_report = workforce.report()
    code = code_workspace.snapshot()
    permissions = {"grants": sorted(cognitive.permissions.grants)}
    ai_status_value = {"providers": ai.status(), "openai": openai_provider.status()}
    plugin_status_value = plugins.status()
    agent_status_value = agent.status()
    self_improvement = self_improver.status()
    identity = deploy_identity()

    return {
        "ok": True,
        "generated_at": __import__("time").time(),
        "human": {
            "headline": "العقل الإلكتروني V12 يعمل كمنظومة إدراك وقرار وتنفيذ وتحقق، مع صلاحيات واضحة.",
            "now": state.get("cognitive_stage", "READY"),
            "status": state.get("status", "READY"),
            "goal": (store.active_goal() or {}).get("text"),
            "decision": state.get("cognitive_trace", {}).get("decision"),
            "next": income.get("next_actions", [])[:4],
            "attention": [
                *([{"level": "NORMAL", "text": "محرك البحث الحي مفعّل ويقبل فقط إعلانات حديثة ذات رابط ودليل زمني؛ لا تُحسب كإيراد."}] if os.getenv("BRAIN_LIVE_INCOME_SEARCH_ENABLED","true").lower()=="true" else [{"level": "ATTENTION", "text": "البحث الحي عن فرص الدخل متوقف."}]),
                *([{"level": "NORMAL", "text": "التطوير الذاتي الكتابي مغلق افتراضياً ويظل محمياً بالموافقة الصريحة."}] if not self_improver.status().get("enabled") else []),
            ],
        },
        "architecture": {
            "core": ["الإدراك", "الذاكرة", "التفكير", "القرار", "التنفيذ", "التحقق", "التعلم"],
            "subsystems": ["Cognitive Loop", "Memory", "Decision", "Tasks", "Permissions", "AI Gateway",
                           "ChatGPT", "Brain Code Agent", "Code Tool", "Workforce", "Income"],
            "tools_count": len(cognitive.tool_catalog()),
            "memory_count": len(store.memories()),
            "event_count": len(store.events(1000)),
        },
        "operation": {
            "cognitive": cognitive_live(),
            "workforce": workforce_report,
            "income": income,
            "permissions": permissions,
            "ai": ai_status_value,
            "plugins": plugin_status_value,
            "agent": agent_status_value,
            "self_improvement": self_improvement,
        },
        "engineering": {
            "code": code,
            "deployment": identity,
        },
        "human_readable_rules": [
            "العقل يشرح ما فهمه قبل أن يقرر عندما تتوفر بيانات كافية.",
            "الفرصة ليست دخلاً؛ لا يُحسب المال إلا بدليل دفع قابل للمطابقة.",
            "التغيير البرمجي يمر بالفحص والنسخ الاحتياطي والتحقق، والكتابة البعيدة محمية بالموافقة.",
            "النشر الخارجي والتحويلات المالية لا تُعرض كمنجزة ما لم توجد نتيجة موثقة وصلاحية فعلية.",
            "الواجهة تعرض الحالة والسبب والخطوة التالية بدلاً من إغراق الإنسان بالتفاصيل الداخلية.",
        ],
    }

@app.get("/api/system/readiness")
def system_readiness():
    """Machine-readable readiness summary for the human interface and deployment checks."""
    checks = []
    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        check("memory", store.state() is not None, "Memory store is readable")
    except Exception as exc:
        check("memory", False, str(exc))
    try:
        tool_count = len(cognitive.tool_catalog())
        check("tools", tool_count > 0, f"{tool_count} tools")
    except Exception as exc:
        check("tools", False, str(exc))
    try:
        check("decision", len(cognitive.decisions.generate("readiness check")) > 0, "Decision engine responds")
    except Exception as exc:
        check("decision", False, str(exc))
    try:
        code = code_workspace.snapshot()
        check("code_workspace", bool(code), "Code workspace snapshot available")
    except Exception as exc:
        check("code_workspace", False, str(exc))

    passed = sum(1 for item in checks if item["ok"])
    return {
        "ok": passed == len(checks),
        "status": "READY" if passed == len(checks) else "DEGRADED",
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "deployment": deploy_identity(),
    }

@app.get("/api/system/diagnostics")
def system_diagnostics():
    checks=[]
    try: checks.append({"name":"memory","ok":bool(store.state() is not None)})
    except Exception as exc: checks.append({"name":"memory","ok":False,"error":str(exc)})
    try: checks.append({"name":"code_workspace","ok":code_tool.verify([]).get("status")=="PASS"})
    except Exception as exc: checks.append({"name":"code_workspace","ok":False,"error":str(exc)})
    checks.append({"name":"tool_router","ok":len(cognitive.tool_catalog())>0})
    checks.append({"name":"decision_engine","ok":len(cognitive.decisions.generate("system diagnostics"))>0})
    return {"ok":all(x["ok"] for x in checks),"checks":checks,"timestamp":__import__("time").time()}

@app.on_event("startup")
def start_background_services():
    try:
        income_strategy.income_engine.discover(20)
    except Exception as exc:
        store.event("INCOME_DISCOVERY_PLAN_FAILED", {"error": str(exc)[:1000]})
    if os.getenv("BRAIN_LIVE_INCOME_SEARCH_ENABLED","true").lower()=="true":
        try: live_income_researcher.run_once()
        except Exception as exc: store.event("LIVE_INCOME_SEARCH_FAILED", {"error": str(exc)[:1000]})
        def live_income_loop():
            import time
            while True:
                time.sleep(max(900, int(os.getenv("BRAIN_LIVE_INCOME_SEARCH_INTERVAL_SECONDS", "1800"))))
                try: live_income_researcher.run_once()
                except Exception as exc: store.event("LIVE_INCOME_SEARCH_FAILED", {"error": str(exc)[:1000]})
        threading.Thread(target=live_income_loop, daemon=True).start()
    if os.getenv("BRAIN_WORKFORCE_ENABLED","true").lower()=="true":
        def workforce_loop():
            import time
            while True:
                time.sleep(max(300, int(os.getenv("BRAIN_WORKFORCE_INTERVAL_SECONDS","900"))))
                try: workforce.dispatch("scheduled_heartbeat", include_revenue=True)
                except Exception as exc: store.event("WORKFORCE_HEARTBEAT_FAILED", {"error": str(exc)[:1000]})
        threading.Thread(target=workforce_loop, daemon=True).start()

@app.get("/api/state")
def state(): return brain.snapshot()
@app.get("/api/messages")
def messages(): return store.messages()

def chatgpt_reply(message,cognitive_context=None):
    recent=store.messages()[-12:]
    context="\n".join(f"{m.get('role','')}: {m.get('content','')}" for m in recent)
    if cognitive_context:
        context += "\n\n[HIGH_LEVEL_COGNITIVE_STATE]\n" + str(cognitive_context)
    return openai_provider.respond(message,context)

@app.post("/api/chat")
def chat(body:Chat):
    message=body.message.strip()
    if not message: return {"ok":False,"error":"EMPTY_MESSAGE"}
    store.add_message("user",message); store.event("PERCEPTION",{"message":message})
    goal=store.active_goal()
    if not goal: store.add_goal(message,.8); goal=store.active_goal()
    loop=cognitive.run(goal["text"])
    selected=loop["decision"].get("selected",{})

    ai_result=chatgpt_reply(message,{"run_id":loop.get("run_id"),"decision":selected.get("action"),"execution":loop.get("execution"),"verification":loop.get("verification"),"learning":loop.get("learning")})
    if ai_result.get("ok"):
        reply=ai_result["reply"]
        source="chatgpt"
    else:
        reply=("تم تشغيل الحلقة المعرفية.\n"
               f"الهدف: {goal['text']}\n"
               f"الحالة: {loop['decision']['status']}\n"
               f"القرار: {selected.get('action','انتظار/موافقة')}\n"
               f"السبب: {loop['decision'].get('reason','—')}")
        source="cognitive_fallback"
    store.add_message("assistant",reply)
    store.event("AI_RESPONSE",{"provider":source})
    decision = loop.get("decision", {}) if isinstance(loop, dict) else {}
    selected = decision.get("selected", {}) if isinstance(decision, dict) else {}
    cognitive_summary = {
        "understood": message,
        "goal": goal.get("text") if isinstance(goal, dict) else message,
        "analysis_status": decision.get("status", "ANALYZING"),
        "decision": selected.get("action", "تحديد الخطوة التالية"),
        "decision_reason": decision.get("reason", "تمت مراجعة الهدف والسياق المتاح."),
        "execution": "لم يُنفذ إجراء خارجي" if source == "chatgpt" else "تم تشغيل الحلقة المعرفية",
        "verification": "الرد الذكي لا يعني أن إجراءً خارجياً تم تنفيذه؛ التنفيذ يحتاج نتيجة موثقة."
    }
    cognitive_summary["run_id"]=loop.get("run_id")
    cognitive_summary["execution_result"]=loop.get("execution",{})
    cognitive_summary["verification_result"]=loop.get("verification",{})
    return {"ok":True,"reply":reply,"provider":source,"cognitive":loop,"cognitive_summary":cognitive_summary,"run_id":loop.get("run_id"),"ai":ai_result if not ai_result.get("ok") else {"ok":True,"provider":"openai","model":openai_provider.model}}

@app.get("/api/memory")
def memory(): return store.memories()
@app.post("/api/memory")
def save_memory(body:Memory): store.save_memory(body.key,body.value); return {"ok":True}
@app.get("/api/goals")
def goals(): return store.goals()
@app.post("/api/goals")
def add_goal(body:Goal): return {"id":store.add_goal(body.text,body.priority)}
@app.post("/api/cycle")
def cycle(): return brain.think()
@app.post("/api/cognitive/run")
def cognitive_run(goal:str): return cognitive.run(goal)

@app.post("/api/problem/solve")
def problem_solve(goal:str):
    """Run the bounded multi-solution problem-solving pipeline with verification and learning."""
    return problem_solver.solve(goal)

@app.get("/api/decision/history")
def decision_history(): return cognitive.decisions.history[-100:]
@app.get("/api/world")
def world(): return cognitive.world.snapshot()
@app.post("/api/world/fact")
def world_fact(key:str,value:str,source:str="user",confidence:float=.8): return cognitive.world.set_fact(key,value,source,confidence)
@app.post("/api/run")
def run_cycle(goal:str="brain_v13"): return cognitive.run(goal)

@app.post("/api/cognitive/start")
def cognitive_start(goal:str="brain_v13"):
    run_id=str(uuid4())
    def worker():
        try:
            cognitive.run(goal,run_id=run_id)
        except Exception as exc:
            state=store.state(); state.update({"status":"ERROR","cognitive_stage":"ERROR","cognitive_trace":{"run_id":run_id,"error":str(exc)}}); store.set_state(state)
            store.event("COGNITIVE_RUN_FAILED",{"run_id":run_id,"error":str(exc)})
    threading.Thread(target=worker,daemon=True).start()
    return {"ok":True,"run_id":run_id,"status":"STARTED"}
@app.post("/api/observe")
def observe(body:Observe): return orchestrator.observe_and_learn(body.actual)
@app.post("/api/learn")
def learn(body:Learn): return brain.learn(body.lesson)
@app.get("/api/events")
def events(): return store.events()

@app.post("/api/code/brain-plan")
def code_brain_plan(body:BrainCodePlanIn):
    try:
        plan=brain_code_agent.plan(body.objective,body.files)
        return brain_code_agent.public_plan(plan)
    except Exception as exc:
        return {"status":"PLAN_FAILED","error":str(exc)}

@app.post("/api/code/brain-apply")
def code_brain_apply(request:Request, body:BrainCodeApplyIn):
    require_control_key(request)
    try:
        plan=brain_code_agent.plan(body.objective,body.files)
        public=brain_code_agent.public_plan(plan)
        if plan.get("status") != "PLAN_READY":
            return public
        result=brain_code_agent.execute_plan(plan,approved=body.approved,commit_message=body.commit_message,persist_to_github=body.persist_to_github)
        store.event("BRAIN_CODE_EVOLUTION",{"status":result.get("status"),"objective":body.objective,"files":body.files})
        return {"plan":public,"execution":result}
    except Exception as exc:
        return {"status":"EXECUTION_FAILED","error":str(exc)}

@app.get("/api/code/status")
def code_status(): return code_team.snapshot()
@app.post("/api/code/inspect")
def code_inspect(path:str): return code_tool.inspect(path)
@app.post("/api/code/preview")
def code_preview(body:CodeChanges):
    changes=[CodeChange(x.path,x.content,x.reason) for x in body.changes]
    return code_tool.preview(changes)
@app.post("/api/code/checkpoint")
def code_checkpoint(body:CodePaths): return code_tool.save_checkpoint(body.paths)
@app.post("/api/code/verify")
def code_verify(body:CodePaths): return code_tool.verify(body.paths)
@app.post("/api/code/apply")
def code_apply(request:Request, body:CodeChanges):
    require_control_key(request)
    if not body.approved:
        return {"ok":False,"status":"EXPLICIT_APPROVAL_REQUIRED","message":"الموافقة الصريحة مطلوبة قبل الكتابة أو الحفظ البعيد."}
    changes=[CodeChange(x.path,x.content,x.reason) for x in body.changes]
    result=code_tool.save_and_execute(changes,reason=body.reason or "controlled code change from Brain interface",commit_message=body.commit_message,persist_to_github=body.persist_to_github)
    store.event("CODE_TOOL_EXECUTION",{"status":result.get("status"),"remote_status":result.get("remote_status"),"paths":[x.path for x in changes]})
    return result

@app.get("/api/code/audit")
def code_audit(): return code_workspace.snapshot()
@app.get("/api/tools")
def tools_catalog(): return {"ok":True,"tools":cognitive.tool_catalog()}
@app.post("/api/tools/execute")
def tools_execute(request:Request,tool_id:str,params:dict|None=None,approved:bool=False):
    require_control_key(request)
    return cognitive.execute_tool(tool_id,params or {},approved)
@app.get("/api/cognitive/history/{run_id}")
def cognitive_history(run_id:str): return {"ok":True,"run_id":run_id,"events":store.events_for_run(run_id,200)}

class EvolutionIn(BaseModel):
    objective:str
    files:list[str]=[]
    approved:bool=False
    persist_to_github:bool=True
    commit_message:str="brain: controlled autonomous improvement"

@app.post("/api/cognitive/evolve")
def cognitive_evolve(request:Request, body:EvolutionIn):
    require_control_key(request)
    if not body.files:
        return {"ok":False,"status":"NO_FILES","message":"حدد الملفات التي يسمح للعقل بتطويرها."}
    checkpoint=code_tool.save_checkpoint(body.files)
    plan=brain_code_agent.plan(body.objective,body.files)
    public=brain_code_agent.public_plan(plan)
    if plan.get("status")!="PLAN_READY":
        return {"ok":True,"status":"PLAN_ONLY","checkpoint":checkpoint,"plan":public}
    if not body.approved:
        return {"ok":True,"status":"WAITING_APPROVAL","checkpoint":checkpoint,"plan":public,"next":"approval_required_for_write"}
    execution=brain_code_agent.execute_plan(plan,approved=True,commit_message=body.commit_message,persist_to_github=body.persist_to_github)
    verification=code_tool.verify(body.files)
    store.event("COGNITIVE_EVOLUTION",{"objective":body.objective,"files":body.files,"execution":execution.get("status"),"verification":verification.get("status")})
    return {"ok":execution.get("status") not in {"EXECUTION_FAILED"},"status":"EVOLUTION_COMPLETE","checkpoint":checkpoint,"plan":public,"execution":execution,"verification":verification}

@app.get("/api/cognitive/live")
def cognitive_live():
    s=store.state(); ev=store.events(40); trace=s.get("cognitive_trace",{}) if isinstance(s,dict) else {}
    return {"ok":True,"state":s,"run_id":trace.get("run_id"),"result":s.get("cognitive_result"),"stage":s.get("cognitive_stage","READY"),"stage_index":s.get("cognitive_stage_index",-1),"total":s.get("cognitive_total",len(cognitive.STAGES)),"trace":trace,"events":ev,"tasks":cognitive.tasks.snapshot()}

@app.get("/api/tasks")
def tasks(): return cognitive.tasks.snapshot()
@app.post("/api/tasks")
def task(title:str,parent_id:str|None=None,depends_on:list[str]=[]): return cognitive.tasks.create(title,parent_id,depends_on)
@app.get("/api/permissions")
def permissions(): return {"grants":sorted(cognitive.permissions.grants)}
@app.post("/api/permissions/grant")
def grant(request:Request, body:Permission):
    require_control_key(request)
    return {"grants":cognitive.permissions.grant(body.capability)}
@app.post("/api/permissions/revoke")
def revoke(request:Request, body:Permission):
    require_control_key(request)
    return {"grants":cognitive.permissions.revoke(body.capability)}
@app.post("/api/permissions/check")
def permission_check(capabilities:list[str],approved:bool=False): return cognitive.permissions.check(capabilities,approved)

@app.post("/api/image-factory/generate")
def image_factory_generate(body:dict):
    """Generate a Brain Image Factory image server-side; API key never reaches the browser."""
    prompt=str(body.get("prompt","")).strip()
    size=str(body.get("size","1024x1024")).strip()
    quality=str(body.get("quality","auto")).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="PROMPT_REQUIRED")
    if not openai_provider.configured:
        return {"ok":False,"error":"OPENAI_NOT_CONFIGURED","message":"Set OPENAI_API_KEY on the server."}
    allowed_sizes={"1024x1024","1536x1024","1024x1536","auto"}
    if size not in allowed_sizes: size="1024x1024"
    payload={"model":os.getenv("OPENAI_IMAGE_MODEL","gpt-image-2"),"prompt":prompt,"size":size}
    if quality in {"low","medium","high","auto"}: payload["quality"]=quality
    headers={"Authorization":f"Bearer {openai_provider.api_key}","Content-Type":"application/json"}
    try:
        import base64, time
        with httpx.Client(timeout=180.0) as client:
            response=client.post(f"{openai_provider.base_url}/images/generations",headers=headers,json=payload)
        if response.status_code >= 400:
            return {"ok":False,"error":"OPENAI_IMAGE_API_ERROR","status_code":response.status_code,"detail":response.text[:2000]}
        data=response.json()
        item=(data.get("data") or [{}])[0]
        b64=item.get("b64_json")
        if not b64:
            return {"ok":False,"error":"IMAGE_DATA_MISSING"}
        media_dir=os.path.join(ROOT,"web","media","generated")
        os.makedirs(media_dir,exist_ok=True)
        filename=f"brain-image-{int(time.time()*1000)}.png"
        path=os.path.join(media_dir,filename)
        with open(path,"wb") as fh: fh.write(base64.b64decode(b64))
        store.event("IMAGE_FACTORY_GENERATED",{"filename":filename,"model":payload["model"],"size":size})
        return {"ok":True,"model":payload["model"],"size":size,"url":f"/media/generated/{filename}","filename":filename}
    except httpx.HTTPError as exc:
        return {"ok":False,"error":"OPENAI_IMAGE_NETWORK_ERROR","detail":str(exc)[:1000]}

@app.get("/api/ai/status")
def ai_status(): return {"providers":ai.status(),"openai":openai_provider.status()}
@app.post("/api/ai/invoke")
def ai_invoke(provider:str,modality:str,payload:dict): return ai.invoke(provider,modality,payload)
@app.post("/api/ai/chat")
def ai_chat(body:Chat):
    result=chatgpt_reply(body.message.strip())
    if result.get("ok"): store.add_message("assistant",result["reply"])
    return result

@app.get("/api/plugins")
def plugin_status(): return plugins.status()
@app.post("/api/plugins/{plugin_id}/enable")
def plugin_enable(request:Request, plugin_id:str):
    require_control_key(request)
    return plugins.enable(plugin_id)
@app.post("/api/plugins/{plugin_id}/disable")
def plugin_disable(request:Request, plugin_id:str):
    require_control_key(request)
    return plugins.disable(plugin_id)

@app.get("/api/agent/status")
def agent_status(): return agent.status()
@app.get("/api/self-improvement/status")
def self_improvement_status(): return self_improver.status()
@app.post("/api/self-improvement/propose")
def self_improvement_propose(body:Improve):
    result=self_improver.propose(body.objective,body.files); store.event("SELF_IMPROVEMENT_PROPOSAL",result); return result
@app.post("/api/self-improvement/record-approval")
def self_improvement_record_approval(request:Request, body:Improve):
    require_control_key(request)
    store.event("SELF_IMPROVEMENT_APPROVAL",{"objective":body.objective,"files":body.files})
    return {"ok":True,"approved":True,"note":"Approval recorded; repository writes remain explicitly gated."}

@app.post("/api/agent/execute")
def agent_execute(request:Request, body:Exec):
    require_control_key(request)
    if not body.approved: return {"ok":False,"error":"EXPLICIT_APPROVAL_REQUIRED"}
    current=brain.snapshot(); current["status"]="ACTING"; store.set_state(current)
    store.event("ACTION_STARTED",{"command":body.command})
    result=agent.execute(body.command,body.cwd,body.timeout)
    current=brain.snapshot(); current.update({"status":"OBSERVING","last_action":body.command,"last_result":result}); store.set_state(current)
    store.event("AGENT_EXECUTION",{"command":body.command,"result":result}); return result

@app.post("/api/builder/plan")
def builder_plan(project:str,objective:str):
    plan=builder.plan(project,objective); store.event("BUILDER_PLAN",plan); return plan

app.mount("/media",StaticFiles(directory=os.path.join(ROOT,"web","media"),check_dir=False),name="media")
app.mount('/media-engine', StaticFiles(directory=os.path.join(ROOT,'web','media-engine'), html=True), name='media-engine')
app.mount('/video-player', StaticFiles(directory=os.path.join(ROOT,'web','video-player'), html=True), name='video-player')
app.mount('/code-hub', StaticFiles(directory=os.path.join(ROOT,'web','code-hub'), html=True), name='code-hub')
app.mount('/browser', StaticFiles(directory=os.path.join(ROOT,'web','browser'), html=True), name='browser')
app.mount('/text-to-drawing', StaticFiles(directory=os.path.join(ROOT,'web','text-to-drawing'), html=True), name='text-to-drawing')
app.mount("/",StaticFiles(directory=os.path.join(ROOT,"web"),html=True),name="ui")
if __name__=="__main__":
    import uvicorn; uvicorn.run(app,host="0.0.0.0",port=int(os.getenv("PORT","8012")))
