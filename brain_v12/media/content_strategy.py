"""Content strategy: turn one verified company project into a bounded content plan."""
from __future__ import annotations

def build_plan(project: dict) -> dict:
    name = project.get("name", "Company project")
    summary = project.get("summary", "")
    return {
        "project": name,
        "source_summary": summary,
        "assets": [
            {"type": "article", "purpose": "project story"},
            {"type": "social_post", "purpose": "short announcement"},
            {"type": "short_video", "purpose": "visual highlight"},
            {"type": "image", "purpose": "campaign visual"},
        ],
        "status": "READY_FOR_FACTORY",
    }
