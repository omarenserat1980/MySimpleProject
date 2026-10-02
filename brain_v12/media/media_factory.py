"""Media factory: package approved source facts into reusable content jobs."""
from __future__ import annotations
from .content_strategy import build_plan
from .media_agent import MediaAgent

class MediaFactory:
    def __init__(self, brand: dict):
        self.brand = brand
        self.agent = MediaAgent(brand)

    def create_campaign(self, project: dict) -> dict:
        plan = build_plan(project)
        draft = self.agent.draft(
            project.get("name", "Project update"),
            [project.get("summary", "")] if project.get("summary") else [],
        )
        return {
            "status": "READY_FOR_REVIEW" if draft["gate"]["ok"] else "BLOCKED",
            "plan": plan,
            "draft": draft,
            "publication": self.agent.publication_action(draft["content"]),
        }
