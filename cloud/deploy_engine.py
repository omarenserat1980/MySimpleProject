"""Controlled local Docker deployment executor for BRAIN Cloud Hub.

The executor is deliberately opt-in. It performs only fixed Docker lifecycle
operations; it never executes an arbitrary shell command supplied by a client.
A Docker daemon/socket must be made available by the self-hosted operator.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}$")
IMAGE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:/@+-]{0,254}$")


class DeployError(RuntimeError):
    pass


def _check_name(name: str) -> str:
    value = name.strip()
    if not NAME_RE.fullmatch(value):
        raise DeployError("invalid service name")
    return value


def _check_image(image: str) -> str:
    value = image.strip()
    if not IMAGE_RE.fullmatch(value):
        raise DeployError("invalid container image")
    return value


def _docker_bin() -> str:
    return os.getenv("BRAIN_DOCKER_BIN", "docker")


def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [_docker_bin(), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DeployError("docker executable is not available") from exc
    except subprocess.TimeoutExpired as exc:
        raise DeployError("docker operation timed out") from exc


def docker_available() -> bool:
    try:
        p = _run(["version", "--format", "{{.Server.Version}}"], timeout=5)
        return p.returncode == 0 and bool(p.stdout.strip())
    except DeployError:
        return False


def deploy(*, name: str, image: str, port: int) -> dict[str, Any]:
    name = _check_name(name)
    image = _check_image(image)
    if not 1 <= port <= 65535:
        raise DeployError("invalid port")
    if not docker_available():
        raise DeployError("local Docker executor is unavailable")

    _run(["rm", "-f", name], timeout=30)
    p = _run([
        "run", "-d",
        "--name", name,
        "--label", "brain.managed=true",
        "--label", f"brain.service={name}",
        "-p", f"{port}:{port}",
        image,
    ], timeout=120)
    if p.returncode != 0:
        raise DeployError(p.stderr[-2000:] or "docker run failed")
    return status(name)


def status(name: str) -> dict[str, Any]:
    name = _check_name(name)
    p = _run([
        "inspect", name,
        "--format",
        "{{json .State}}",
    ])
    if p.returncode != 0:
        return {"name": name, "status": "NOT_FOUND"}
    try:
        state = json.loads(p.stdout)
    except json.JSONDecodeError:
        state = {"raw": p.stdout.strip()}
    return {"name": name, "status": state.get("Status", "UNKNOWN"), "state": state}


def restart(name: str) -> dict[str, Any]:
    name = _check_name(name)
    p = _run(["restart", name], timeout=60)
    if p.returncode != 0:
        raise DeployError(p.stderr[-2000:] or "docker restart failed")
    return status(name)


def stop(name: str) -> dict[str, Any]:
    name = _check_name(name)
    p = _run(["stop", name], timeout=60)
    if p.returncode != 0:
        raise DeployError(p.stderr[-2000:] or "docker stop failed")
    return status(name)


def logs(name: str, tail: int = 200) -> dict[str, Any]:
    name = _check_name(name)
    tail = max(1, min(1000, int(tail)))
    p = _run(["logs", "--tail", str(tail), name], timeout=30)
    if p.returncode != 0:
        raise DeployError(p.stderr[-2000:] or "docker logs failed")
    return {"name": name, "tail": tail, "logs": p.stdout[-20000:]}
