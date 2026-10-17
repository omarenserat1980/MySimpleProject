"""Reliable, read-only deployment identity using provider-native metadata."""
from __future__ import annotations

from typing import Mapping


def deployment_identity(env: Mapping[str, str] | None = None) -> dict[str, object]:
    """Resolve Render or GitHub deployment metadata without trusting stale fallback values."""
    if env is None:
        import os
        env = os.environ

    render_commit = (env.get("RENDER_GIT_COMMIT") or "").strip()
    github_sha = (env.get("GITHUB_SHA") or "").strip()
    legacy_commit = (env.get("GIT_COMMIT") or "").strip()
    expected_commit = render_commit or github_sha

    commit = render_commit or github_sha or legacy_commit or "unknown"
    return {
        "commit": commit,
        "expected_commit": expected_commit,
        "converged": bool(expected_commit and commit == expected_commit),
        "branch": (env.get("RENDER_GIT_BRANCH") or env.get("GITHUB_REF_NAME") or "unknown").strip(),
        "repository": (env.get("RENDER_GIT_REPO_SLUG") or env.get("GITHUB_REPOSITORY") or "unknown").strip(),
        "service_id": (env.get("RENDER_SERVICE_ID") or "unknown").strip(),
        "run_id": (env.get("GITHUB_RUN_ID") or "unknown").strip(),
        "instance": (env.get("RENDER_INSTANCE_ID") or env.get("HOSTNAME") or "unknown").strip(),
    }
