"""Evidence-first robotics research catalog for Electronic Brain V12.

This is a curated knowledge seed, not a robot controller. It records primary
project links and integration lessons without copying third-party code,
installing packages, requiring hardware, or enabling external actions.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

MEMORY_KEY = "research.robotics.open_source.catalog.v1"
RESEARCH_CUTOFF = "2026-10-17"

PROJECTS = [
    {
        "id": "lerobot",
        "name": "LeRobot",
        "url": "https://github.com/huggingface/lerobot",
        "evidence_url": "https://arxiv.org/html/2602.22818v1",
        "domain": "robot_learning",
        "human_benefit": ["lower-cost robotics research", "reusable learning from demonstrations"],
        "lesson": "Store demonstrations, task context, evaluation metrics, and failures as reusable evidence rather than unverified success claims.",
        "brain_application": "Add versioned experiment records with task, dataset provenance, environment, metrics, failure modes, and reproducibility metadata.",
        "license_status": "REVIEW_CODE_WEIGHTS_AND_DATA_SEPARATELY",
        "compute_profile": "SOFTWARE_ONLY_CATALOG; training and some inference can require substantial GPU resources",
        "integration_priority": 1,
    },
    {
        "id": "eclipse_ditto",
        "name": "Eclipse Ditto",
        "url": "https://github.com/eclipse-ditto/ditto",
        "evidence_url": "https://github.com/eclipse-ditto/ditto",
        "domain": "digital_twin_and_state",
        "human_benefit": ["system reliability", "maintenance", "interoperable monitoring"],
        "lesson": "Represent current state, historical observations, and desired state separately, with explicit timestamps and interfaces.",
        "brain_application": "Use a typed state/provenance model for software nodes and services; do not infer a live node from a catalog entry.",
        "license_status": "VERIFY_CURRENT_LICENSE_AND_DEPENDENCIES",
        "compute_profile": "SOFTWARE_ONLY_CATALOG; a deployed Ditto stack adds operational dependencies",
        "integration_priority": 1,
    },
    {
        "id": "hy_embodied_0_5_x",
        "name": "HY-Embodied-0.5-X",
        "url": "https://github.com/Tencent-Hunyuan/HY-Embodied-0.5-X",
        "evidence_url": "https://github.com/Tencent-Hunyuan/HY-Embodied-0.5-X",
        "domain": "embodied_multimodal_reasoning",
        "human_benefit": ["more capable task understanding", "manipulation risk analysis research"],
        "lesson": "Separate spatial/task interpretation, candidate action prediction, risk assessment, and outcome verification.",
        "brain_application": "Represent these as separate plan fields and never treat predicted actions as executed actions.",
        "license_status": "VERIFY_MODEL_CODE_DATA_AND_COMMERCIAL_TERMS",
        "compute_profile": "SOFTWARE_ONLY_CATALOG; model runtime and GPU needs must be measured before adoption",
        "integration_priority": 2,
    },
    {
        "id": "isaac_lab",
        "name": "Isaac Lab",
        "url": "https://github.com/isaac-sim/IsaacLab",
        "evidence_url": "https://isaac-sim.github.io/IsaacLab/",
        "domain": "simulation_and_robot_learning",
        "human_benefit": ["safer pre-deployment testing", "reproducible robotics experiments"],
        "lesson": "Test policies in simulation, measure failures, and record simulator/version assumptions before any real-world transfer.",
        "brain_application": "Create simulation-only evaluation jobs and require explicit evidence before promoting a policy or plan to a higher-risk stage.",
        "license_status": "DOCUMENTATION_REPORTS_BSD_3_CLAUSE_WITH_SOME_APACHE_2_0_PARTS_VERIFY_COMPONENTS",
        "compute_profile": "SOFTWARE_ONLY_CATALOG; full simulation may require a compatible GPU and significant disk/RAM",
        "integration_priority": 2,
    },
    {
        "id": "ros2_nav2_moveit2",
        "name": "ROS 2 + Nav2 + MoveIt 2",
        "url": "https://github.com/ros2/ros2",
        "evidence_url": "https://github.com/ros-navigation/navigation2",
        "domain": "robot_middleware_navigation_manipulation",
        "human_benefit": ["accessible assistive and agricultural robotics research", "interoperability"],
        "lesson": "Make capabilities, inputs, outputs, permissions, and failure states explicit behind adapters.",
        "brain_application": "Reuse the adapter/capability-registry pattern for software nodes; never enable physical actuation from this catalog.",
        "license_status": "CHECK_EACH_REPOSITORY_AND_DEPENDENCY; ROS_2_CORE_IS_APACHE_2_0",
        "compute_profile": "SOFTWARE_ONLY_CATALOG; live robot use is explicitly out of scope for this seed",
        "integration_priority": 3,
    },
    {
        "id": "openvla",
        "name": "OpenVLA",
        "url": "https://github.com/openvla/openvla",
        "evidence_url": "https://arxiv.org/html/2406.09246v2",
        "domain": "vision_language_action_research",
        "human_benefit": ["open research in language-conditioned manipulation"],
        "lesson": "Model weights, code, datasets, and downstream actions need separate license and safety reviews.",
        "brain_application": "Treat as an optional research reference, not a default runtime or a memory engine; benchmark cost and model license first.",
        "license_status": "CODE_AND_MODEL_WEIGHT_TERMS_MUST_BE_REVIEWED_SEPARATELY",
        "compute_profile": "SOFTWARE_ONLY_CATALOG; reported inference/training requirements can be high",
        "integration_priority": 3,
    },
]


def snapshot() -> dict:
    """Return a deterministic, reviewable catalog with an explicit evidence boundary."""
    return {
        "schema_version": 1,
        "catalog_id": MEMORY_KEY,
        "research_cutoff": RESEARCH_CUTOFF,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_policy": {
            "web_search_scope": "broad public-web survey; not an exhaustive search of every website",
            "primary_sources_preferred": True,
            "repository_activity_verified_for_every_entry": False,
            "license_verified_for_every_component": False,
            "live_hardware_or_agent_presence_proven": False,
            "copy_third_party_code": False,
            "auto_install_dependencies": False,
            "enable_external_actions": False,
            "default_mode": "READ_ONLY_RESEARCH_AND_SOFTWARE_SIMULATION",
        },
        "projects": PROJECTS,
        "adoption_gate": [
            "recheck repository activity and release/commit dates",
            "review code, model-weight, dataset, and transitive dependency licenses separately",
            "document compute, security, privacy, and maintenance requirements",
            "run isolated tests and reproducible benchmarks",
            "record measured evidence before changing priority or enabling execution",
            "require explicit authorization for deployments, credentials, or physical actuation",
        ],
    }


def persist_to_memory(store) -> dict:
    """Explicitly persist the catalog through Brain's existing MemoryStore interface."""
    data = snapshot()
    store.save_memory(MEMORY_KEY, json.dumps(data, ensure_ascii=False, sort_keys=True))
    store.event("OPEN_SOURCE_ROBOTICS_RESEARCH_CATALOG_SAVED", {
        "catalog_id": MEMORY_KEY,
        "project_count": len(PROJECTS),
        "research_cutoff": RESEARCH_CUTOFF,
        "mode": "READ_ONLY_RESEARCH_AND_SOFTWARE_SIMULATION",
    })
    return {
        "ok": True,
        "memory_key": MEMORY_KEY,
        "project_count": len(PROJECTS),
        "side_effects": ["Brain MemoryStore updated when this function is explicitly called"],
        "external_actions_enabled": False,
        "dependencies_installed": False,
    }
