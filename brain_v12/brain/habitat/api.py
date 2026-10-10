"""Brain Habitat HTTP control plane."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Request

from ..control_auth import require_control_key
from .capability_manager import CapabilityManager
from .project_factory import ProjectFactory
from .source_explorer import SourceExplorer

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_HOME = Path(os.getenv("BRAIN_RUNTIME_HOME", "~/.brain/runtime")).expanduser()
STATE = Path(os.getenv("BRAIN_HABITAT_STATE", RUNTIME_HOME / "state" / "habitat_capabilities.json")).expanduser()
WORKSPACE = Path(os.getenv("BRAIN_HABITAT_WORKSPACE", RUNTIME_HOME / "habitat" / "projects")).expanduser()
SOURCE_ROOTS = [Path(x).resolve() for x in os.getenv(
    "BRAIN_HABITAT_SOURCE_ROOTS", str(ROOT / "brain_v12")
).split(os.pathsep) if x.strip()]

capabilities = CapabilityManager(STATE)
projects = ProjectFactory(WORKSPACE)
sources = SourceExplorer(SOURCE_ROOTS)

router = APIRouter(prefix="/api/habitat", tags=["brain-habitat"])


@router.get("/status")
def status():
    return {
        "ok": True,
        "workspace": str(WORKSPACE),
        "source_roots": [str(x) for x in SOURCE_ROOTS],
        "capabilities": capabilities.status()["capabilities"],
    }


@router.post("/capabilities/{name}")
def set_capability(name: str, request: Request, enabled: bool = True):
    require_control_key(request)
    return capabilities.declare(name, enabled)


@router.post("/projects")
def create_project(request: Request, body: dict):
    require_control_key(request)
    return projects.create(str(body.get("name", "")), str(body.get("kind", "python")))


@router.get("/sources")
def list_sources(limit: int = 200):
    return {"ok": True, "files": sources.list_files(limit=max(1, min(limit, 500)))}


@router.get("/sources/read")
def read_source(path: str, request: Request):
    require_control_key(request)
    return {"ok": True, "path": path, "content": sources.read(path)}


@router.post("/android/open-app-test")
def android_open_app_test(request: Request, package: str = "com.android.settings"):
    """Queue a least-privilege Android app-open test through the live Executor gate."""
    require_control_key(request)
    from ..device_bridge import DeviceBridge
    bridge = DeviceBridge()
    result = bridge.enqueue("open_app", {"package": package})
    return result


@router.post("/android/project-test")
def android_project_test(request: Request, name: str = "BrainHabitatTest"):
    """Create a tiny project through the live Android Executor gate."""
    require_control_key(request)
    from ..device_bridge import DeviceBridge
    files = {
        "README.md": "# Brain Habitat Android Test\n\nCreated through the controlled Android Executor path.\n",
        "src/BrainHabitatTest.txt": "BRAIN_HABITAT_ANDROID_EXECUTOR_OK\n",
    }
    bridge = DeviceBridge()
    return bridge.enqueue("create_app_project", {"name": name, "files": files})
