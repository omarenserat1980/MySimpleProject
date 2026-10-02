"""Press-ready fact sheet generator using only supplied evidence."""
from __future__ import annotations

def fact_sheet(project: dict) -> dict:
    return {
        "title": project.get("name", ""),
        "summary": project.get("summary", ""),
        "evidence": list(project.get("evidence", [])),
        "status": "READY_FOR_REVIEW",
    }
