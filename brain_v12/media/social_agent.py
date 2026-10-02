"""Social copy generator; publication remains separately authorized."""
from __future__ import annotations

def create_post(project: dict, platform: str = "generic") -> dict:
    name = project.get("name", "Project update")
    summary = project.get("summary", "")
    return {
        "platform": platform,
        "content": f"{name}: {summary}".strip(),
        "status": "READY_FOR_REVIEW",
        "publication": "REQUIRES_AUTHORIZATION",
    }
