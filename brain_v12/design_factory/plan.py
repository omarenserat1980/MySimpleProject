"""Prepare an evidence-aware design plan; never execute tasks implicitly."""
from __future__ import annotations

from .task_router import route_task
from .registry import load_registry

DOMAIN_GATES = {
    "discovery": ["G0_DISCOVERY"],
    "requirements": ["G1_REQUIREMENTS"],
    "architecture": ["G2_ARCHITECTURE"],
    "detailed_design": ["G2_ARCHITECTURE"],
    "software": ["G3_IMPLEMENTATION", "G4_TESTS", "G5_EVIDENCE", "G6_SECURITY"],
    "digital_logic": ["G3_IMPLEMENTATION", "G4_TESTS", "G5_EVIDENCE", "G6_SECURITY"],
    "physical_design": ["G4_TESTS", "G5_EVIDENCE", "G6_SECURITY", "G7_PHYSICAL"],
    "simulation": ["G4_TESTS", "G5_EVIDENCE"],
    "security": ["G6_SECURITY"],
    "verification": ["G4_TESTS", "G5_EVIDENCE"],
    "infrastructure": ["G3_IMPLEMENTATION", "G4_TESTS", "G5_EVIDENCE", "G6_SECURITY"],
    "manufacturing": ["G5_EVIDENCE", "G6_SECURITY", "G7_PHYSICAL", "G8_MANUFACTURING"],
    "reliability": ["G4_TESTS", "G5_EVIDENCE", "G6_SECURITY"],
    "integration": ["G4_TESTS", "G5_EVIDENCE", "G6_SECURITY", "G9_RELEASE"],
    "new_domain": ["G0_DISCOVERY", "G1_REQUIREMENTS", "G5_EVIDENCE", "G6_SECURITY"],
}

DOMAIN_ORDER = [
    "discovery", "requirements", "architecture", "detailed_design",
    "software", "digital_logic", "simulation", "security", "verification",
    "infrastructure", "physical_design", "manufacturing", "reliability",
    "integration", "new_domain",
]

def prepare_design_plan(description: str) -> dict:
    """Return a reviewable plan; no tools, files, devices, or external services are run."""
    routed = route_task(description)
    domains = sorted(set(routed["domains"]), key=lambda d: DOMAIN_ORDER.index(d) if d in DOMAIN_ORDER else len(DOMAIN_ORDER))
    registry = load_registry()
    prompt_by_id = {item["id"]: item for item in registry["prompts"]}
    selected_prompts = [
        {"id": prompt_id, "name": prompt_by_id[prompt_id]["name"], "path": prompt_by_id[prompt_id]["path"]}
        for prompt_id in routed["prompt_ids"] if prompt_id in prompt_by_id
    ]
    gates = []
    for domain in domains:
        for gate in DOMAIN_GATES.get(domain, ["G5_EVIDENCE"]):
            if gate not in gates:
                gates.append(gate)
    return {
        "status": "PLANNED",
        "task": description.strip(),
        "domains": domains,
        "prompt_ids": routed["prompt_ids"],
        "selected_prompts": selected_prompts,
        "required_gates": gates,
        "review_required": True,
        "execution_started": False,
        "limits": [
            "Planning does not execute code or operate external systems.",
            "Unavailable tools and missing evidence must remain BLOCKED.",
            "Simulation cannot satisfy hardware, manufacturing, mining, or revenue proof.",
            "Merge, deployment, spending, secret changes, and fabrication require separate authorization."
        ],
    }
