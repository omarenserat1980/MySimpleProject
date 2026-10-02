"""Bounded media agent for company-owned communications."""
from __future__ import annotations
from .content_quality_gate import validate

class MediaAgent:
    def __init__(self, brand: dict):
        self.brand = brand

    def draft(self, topic: str, facts: list[str] | None = None) -> dict:
        facts = facts or []
        body = "\n".join(facts)
        text = f"{self.brand.get('company_name', 'Company')}: {topic}.\n{body}".strip()
        gate = validate(text, self.brand)
        return {"status": "READY_FOR_REVIEW" if gate["ok"] else "BLOCKED", "content": text, "gate": gate}

    def publication_action(self, content: str) -> dict:
        return {
            "status": "REQUIRES_AUTHORIZATION",
            "action": "publish_external",
            "content": content,
        }
