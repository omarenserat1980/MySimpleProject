#!/usr/bin/env python3
"""Deterministic Brain V12 preflight checks.

This module is intentionally dependency-light so CI can run it before the
container image is built and the same checks can be reused inside the image.
"""
from __future__ import annotations

import importlib
import os
import pathlib
import sys
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[2]


def fail(message: str) -> None:
    print(f"[brain-v12][FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def require_files(paths: Iterable[str]) -> None:
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            fail(f"required file missing: {relative}")


def require_dirs(paths: Iterable[str]) -> None:
    for relative in paths:
        path = ROOT / relative
        if not path.is_dir():
            fail(f"required directory missing: {relative}")


def compile_tree() -> None:
    import compileall

    if not compileall.compile_dir(str(ROOT / "brain_v12"), quiet=1):
        fail("brain_v12 compilation failed")


def import_application() -> None:
    try:
        module = importlib.import_module("brain_v12.app")
        application = getattr(module, "app", None)
    except Exception as exc:
        fail(f"brain_v12.app import failed: {type(exc).__name__}: {exc}")
    if application is None:
        fail("brain_v12.app does not expose FastAPI 'app'")


def require_routes(routes: Iterable[str]) -> None:
    from brain_v12.app import app

    available = {getattr(route, "path", "") for route in app.routes}
    missing = sorted(set(routes) - available)
    if missing:
        fail(f"required routes missing: {missing}")


def main() -> int:
    require_files(
        (
            "brain_v12/app.py",
            "brain_v12/Dockerfile",
            "brain_v12/requirements.txt",
        )
    )
    require_dirs(("brain_v12/brain", "brain_v12/movie_summary_factory", "brain_v7"))
    compile_tree()
    import_application()
    require_routes(("/health", "/api/system/readiness", "/api/deploy/verify"))
    print("[brain-v12][PASS] preflight complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
