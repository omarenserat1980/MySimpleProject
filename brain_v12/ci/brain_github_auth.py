#!/usr/bin/env python3
"""Brain GitHub authentication and Actions diagnostics.

Never prints token values. Uses BRAIN_GITHUB_TOKEN, GITHUB_TOKEN or GH_TOKEN.
"""
from __future__ import annotations
import json, os, sys, urllib.error, urllib.request

REPO = os.getenv("BRAIN_GITHUB_REPOSITORY") or os.getenv("GITHUB_REPOSITORY") or "omarenserat1980/MySimpleProject"
TOKEN = os.getenv("BRAIN_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

def request(path: str):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Brain-GitHub-Auth-Diagnostics",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, json.loads(r.read().decode("utf-8"))

def main() -> int:
    result = {
        "schema": "brain-github-auth/v1",
        "token_configured": bool(TOKEN),
        "token_source": (
            "BRAIN_GITHUB_TOKEN" if os.getenv("BRAIN_GITHUB_TOKEN") else
            "GITHUB_TOKEN" if os.getenv("GITHUB_TOKEN") else
            "GH_TOKEN" if os.getenv("GH_TOKEN") else None
        ),
        "repository": REPO,
    }
    if not TOKEN:
        result["status"] = "TOKEN_MISSING"
        print(json.dumps(result, indent=2))
        return 2
    try:
        code, user = request("/user")
        result["api_user"] = {"ok": code == 200, "login": user.get("login"), "status": code}
        code, repo = request("/repos/" + REPO)
        result["repository_access"] = {
            "ok": code == 200,
            "full_name": repo.get("full_name"),
            "private": repo.get("private"),
            "default_branch": repo.get("default_branch"),
            "permissions": repo.get("permissions", {}),
            "status": code,
        }
        code, actions = request("/repos/" + REPO + "/actions/workflows")
        result["actions_access"] = {"ok": code == 200, "status": code, "workflow_count": len(actions.get("workflows", []))}
        result["status"] = "PASS" if result["api_user"]["ok"] and result["repository_access"]["ok"] and result["actions_access"]["ok"] else "FAIL"
    except urllib.error.HTTPError as exc:
        result["status"] = "FAIL"
        result["http_error"] = exc.code
        if exc.code in (401, 403):
            result["hint"] = "Authentication or token permissions are insufficient."
        elif exc.code == 404:
            result["hint"] = "Repository/workflow is not visible to this token, or the path is wrong."
    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
