from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_legacy_brain6_launcher_is_disabled():
    launcher = read("scripts/brain6_168h.sh")
    state = json.loads(read("production/BRAIN6_168H.json"))
    assert "exit 78" in launcher
    assert "background_factory_worker" not in launcher
    assert state["enabled"] is False
    assert state["retired"] is True


def test_active_cloud_supervisors_do_not_call_v7_factory():
    for path in ("cloud/brain_cloud.py", "cloud/brain_internet_cloud.py", "cloud/film_reliability.py"):
        assert "brain_v7.braincore_v2.background_factory_worker" not in read(path)
    assert "BRAIN_V12_RENDERER_NOT_INTEGRATED" in read("cloud/film_reliability.py")


def test_cloud_verification_targets_v12_only():
    factory = read("cloud/autonomous_software_factory.py")
    loop = read("cloud/self_improvement_loop.py")
    assert '"brain_v12"' in factory
    assert '"brain_v12/tests"' in factory
    assert '"brain_v12/tests"' in loop
    assert "brain_v7/tests" not in factory
    assert "brain_v7/tests" not in loop


def test_legacy_named_container_files_launch_v12():
    for path in ("brain_v7/Dockerfile", "brain_v7/Dockerfile.core"):
        dockerfile = read(path)
        assert "python -m brain_v12.app" in dockerfile
        assert "brain_v7.braincore_v2" not in dockerfile
    assert "python -m brain_v12.app" in read("brain_v7/docker-compose.autonomous.yml")
