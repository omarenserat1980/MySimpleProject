#!/usr/bin/env python3
"""Deterministic build/runtime preflight for Electronic Brain V12/V14."""
from __future__ import annotations
import importlib, os, pathlib, sys
from typing import Iterable
ROOT=pathlib.Path(__file__).resolve().parents[2]
def fail(message:str)->None:
    print(f"[brain-v12][FAIL] {message}",file=sys.stderr); raise SystemExit(1)
def require_files(paths:Iterable[str])->None:
    for relative in paths:
        if not (ROOT/relative).is_file(): fail(f"required file missing: {relative}")
def require_dirs(paths:Iterable[str])->None:
    for relative in paths:
        if not (ROOT/relative).is_dir(): fail(f"required directory missing: {relative}")
def compile_tree()->None:
    import compileall
    if not compileall.compile_dir(str(ROOT/"brain_v12"),quiet=1): fail("brain_v12 compilation failed")
def import_application():
    try:
        module=importlib.import_module("brain_v12.app"); application=getattr(module,"app",None)
    except Exception as exc: fail(f"brain_v12.app import failed: {type(exc).__name__}: {exc}")
    if application is None: fail("brain_v12.app does not expose FastAPI 'app'")
    return application
def require_routes(application,routes:Iterable[str])->None:
    available={getattr(route,"path","") for route in getattr(application,"routes",[])}
    missing=sorted(set(routes)-available)
    if missing: fail(f"required routes missing: {missing}")
def main()->int:
    require_files(("brain_v12/app.py","brain_v12/Dockerfile","brain_v12/requirements.txt","brain_v12/tools/ci_preflight.py"))
    require_dirs(("brain_v12/brain","brain_v12/movie_summary_factory","brain_v7"))
    os.environ.setdefault("BRAIN_DB","/tmp/brain-v12-preflight.db")
    os.environ.setdefault("BRAIN_LIVE_INCOME_SEARCH_ENABLED","false")
    os.environ.setdefault("BRAIN_WORKFORCE_ENABLED","false")
    os.environ.setdefault("    os.environ.setdefault("BRAIN_V14_VERSION","14.0")
    compile_tree()
    application=import_application()
    require_routes(application,("/health","/api/system/readiness","/api/system/diagnostics","/api/deploy/verify"))
    from fastapi.testclient import TestClient
    response=TestClient(application).get("/health")
    if response.status_code!=200: fail(f"/health returned HTTP {response.status_code}")
    payload=response.json()
    if payload.get("ok") is not True: fail(f"/health contract failed: {payload}")
    print("[brain-v12][PASS] preflight complete"); return 0
if __name__=="__main__": raise SystemExit(main())
