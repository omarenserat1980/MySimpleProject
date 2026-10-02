"""Collect public GitHub opportunity signals without contacting anyone."""
from __future__ import annotations

def normalize_issue(issue: dict) -> dict:
    repo = issue.get("repository_url", "").rstrip("/").split("/")
    repo_name = "/".join(repo[-2:]) if len(repo) >= 2 else ""
    return {
        "source": "github_public_issue",
        "customer_hint": repo_name,
        "problem": issue.get("title", "").strip(),
        "evidence_url": issue.get("html_url", ""),
        "evidence": issue.get("body", "")[:1000],
        "location": "global",
        "urgency": "unknown",
        "external_contact": "REQUIRES_AUTHORIZATION",
        "status": "READY_FOR_REVIEW" if issue.get("html_url") and issue.get("title") else "INCOMPLETE",
    }

def collect_from_search_payload(payload: dict) -> list[dict]:
    return [normalize_issue(x) for x in payload.get("items", []) if isinstance(x, dict)]
