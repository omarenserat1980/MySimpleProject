"""Audited catalog of initial services."""
from __future__ import annotations

OFFERS = [
    {
        "id":"OFFER-AUTOMATION-001",
        "name":"AI Workflow Automation",
        "customer_problem":"repetitive manual digital workflows",
        "deliverables":["workflow assessment","automation prototype","verification report"],
        "pricing":"CUSTOM_QUOTE",
    },
    {
        "id":"OFFER-MEDIA-001",
        "name":"Cinematic Media Package",
        "customer_problem":"need for short-form branded visual content",
        "deliverables":["short video","social assets","quality report"],
        "pricing":"CUSTOM_QUOTE",
    },
    {
        "id":"OFFER-CI-001",
        "name":"GitHub CI Reliability Package",
        "customer_problem":"repeated CI failures and slow recovery",
        "deliverables":["failure diagnosis","bounded repair","verification evidence"],
        "pricing":"CUSTOM_QUOTE",
    },
]

def find_matches(problem: str) -> list[dict]:
    p=problem.lower()
    return [o for o in OFFERS if any(k in p for k in (
        "automation","workflow","manual","video","media","content","github","ci","pipeline"
    ))]
