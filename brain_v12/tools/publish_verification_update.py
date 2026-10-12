#!/usr/bin/env python3
"""Publish a current-head, evidence-backed GitHub Actions update on an open PR."""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import datetime, timezone
from typing import Any

MARKER = "<!-- brain-verification-update:v1 -->"
REQUIRED_WORKFLOWS = (
    "Golden Loop Accelerator",
    "Brain Fabric Tests",
    "Brain Reasoning Loop",
    "Brain Reflection E2E",
    "Brain Cloud Mining Control Plane",
)

def gh_api(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    cmd = ["gh", "api", path, "--method", method]
    if payload is not None:
        cmd.extend(["--input", "-"])
    result = subprocess.run(cmd, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"gh api failed: {path}")
    return json.loads(result.stdout) if result.stdout.strip() else {}

def latest_workflow_states(runs: list[dict[str, Any]], head_sha: str) -> dict[str, dict[str, Any] | None]:
    states = {name: None for name in REQUIRED_WORKFLOWS}
    for run in sorted(runs, key=lambda r: r.get("created_at", ""), reverse=True):
        if run.get("head_sha") != head_sha:
            continue
        name = str(run.get("name") or "")
        for required in REQUIRED_WORKFLOWS:
            if states[required] is None and (name == required or required in name):
                states[required] = run
    return states

def render_comment(pr_number: int, head_sha: str, states: dict[str, dict[str, Any] | None]) -> str:
    passed = all(run is not None and run.get("status") == "completed" and run.get("conclusion") == "success"
                 for run in states.values())
    lines = [
        MARKER, "## Brain verification update", "",
        f"- PR: #{pr_number}",
        f"- Head commit: {head_sha}",
        f"- Evidence checked (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"- CI verdict: **{'PASS' if passed else 'BLOCKED / INCOMPLETE'}**", "",
        "| Required workflow | Result | Run |", "|---|---|---|",
    ]
    for name in REQUIRED_WORKFLOWS:
        run = states[name]
        if run is None:
            result, link = "MISSING for this exact head", "—"
        else:
            result = f"{run.get('status', 'unknown')} / {run.get('conclusion') or 'in progress'}"
            url = run.get("html_url")
            link = f"[run {run.get('id')}]({url})" if url else f"run {run.get('id', 'unknown')}"
        lines.append(f"| {name} | {result} | {link} |")
    lines.extend([
        "",
        "> CI results apply only to this exact PR head. They do not prove a signed execution contract, trusted runner authorization, a real Windows Server guest boot, or independent completion-gate success."
    ])
    return "\n".join(lines)

def publish(repo: str, pr_number: int) -> str:
    pr = gh_api(f"repos/{repo}/pulls/{pr_number}")
    if pr.get("state") != "open":
        raise RuntimeError(f"PR #{pr_number} is not open; refusing to publish.")
    head_sha = pr.get("head", {}).get("sha")
    if not head_sha:
        raise RuntimeError("GitHub did not return the PR head SHA.")
    response = gh_api(f"repos/{repo}/actions/runs?head_sha={head_sha}&event=pull_request&per_page=100")
    states = latest_workflow_states(response.get("workflow_runs", []), head_sha)
    body = render_comment(pr_number, head_sha, states)
    comments = gh_api(f"repos/{repo}/issues/{pr_number}/comments?per_page=100")
    existing = next((c for c in comments if MARKER in (c.get("body") or "")), None)
    if existing:
        gh_api(f"repos/{repo}/issues/comments/{existing['id']}", "PATCH", {"body": body})
        action = f"Updated verification comment {existing.get('html_url', '')}"
    else:
        created = gh_api(f"repos/{repo}/issues/{pr_number}/comments", "POST", {"body": body})
        action = f"Created verification comment {created.get('html_url', '')}"
    passed = all(states[n] and states[n].get("status") == "completed" and states[n].get("conclusion") == "success"
                 for n in REQUIRED_WORKFLOWS)
    return f"{action}\nHead: {head_sha}\nVerdict: {'PASS' if passed else 'BLOCKED / INCOMPLETE'}"

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "omarenserat1980/MySimpleProject"))
    parser.add_argument("--pr", type=int, required=True, help="Open pull request number")
    args = parser.parse_args()
    if not (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        print("ERROR: GH_TOKEN/GITHUB_TOKEN is required; token values are never printed.", file=sys.stderr)
        return 2
    try:
        print(publish(args.repo, args.pr))
        return 0
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
