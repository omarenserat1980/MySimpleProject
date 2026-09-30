"""Open-source intelligence layer for Brain.

This module distills reusable engineering patterns from selected open-source
projects into Brain-native, dependency-free design knowledge. It does not copy
third-party code or auto-install anything.
"""
from __future__ import annotations
import json, time
from pathlib import Path

PATTERNS = [
    {
        "id": "durable_execution",
        "sources": ["Temporal", "Apache Airflow", "Kestra"],
        "lesson": "Represent work as explicit steps with state, retries, dependencies, and resumability.",
        "brain_application": "Track every Brain job as a checkpointed state machine so a failed step can resume instead of restarting the whole pipeline.",
        "capability": "reliable_workflow_execution",
    },
    {
        "id": "agent_sandboxing",
        "sources": ["OpenHands"],
        "lesson": "Agents need bounded workspaces, explicit tools, observable actions, and isolated execution.",
        "brain_application": "Separate planning from execution and keep high-impact/external actions behind explicit policy gates.",
        "capability": "safe_agent_execution",
    },
    {
        "id": "graph_workflows",
        "sources": ["ComfyUI"],
        "lesson": "Complex media generation becomes composable when capabilities are represented as a graph of reusable nodes.",
        "brain_application": "Represent film production as capability nodes with explicit inputs, outputs, and fallbacks.",
        "capability": "composable_media_pipeline",
    },
    {
        "id": "multimodal_generation",
        "sources": ["LTX-2"],
        "lesson": "Video generation benefits from synchronized audio/video, keyframes, conditioning, and reusable control models.",
        "brain_application": "Make the film planner backend-agnostic while exposing audio/video/keyframe requirements to capable runtimes.",
        "capability": "multimodal_film_generation",
    },
    {
        "id": "semantic_memory",
        "sources": ["Qdrant"],
        "lesson": "Memory is more useful when facts are searchable semantically and can be filtered by metadata.",
        "brain_application": "Store Brain observations, successful recipes, failures, and provenance as retrievable knowledge.",
        "capability": "semantic_learning_memory",
    },
    {
        "id": "local_model_runtime",
        "sources": ["Ollama", "llama.cpp"],
        "lesson": "Model backends should be replaceable behind stable local APIs and capability contracts.",
        "brain_application": "Keep reasoning and generation behind adapters so Brain can select the best available local backend without hard coupling.",
        "capability": "backend_portability",
    },
    {
        "id": "observability_and_evaluation",
        "sources": ["Langfuse", "Arize Phoenix"],
        "lesson": "AI systems improve when traces, prompts, tool calls, outcomes, datasets, and evaluations are first-class artifacts.",
        "brain_application": "Record structured execution traces and score outcomes before allowing learned routing preferences to change.",
        "capability": "continuous_evaluation",
    },
]

def snapshot() -> dict:
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "policy": {
            "copy_third_party_code": False,
            "auto_install_dependencies": False,
            "external_side_effects": "policy_gated",
        },
        "patterns": PATTERNS,
    }

def write_snapshot(directory: str = "brain6_artifacts") -> dict:
    data = snapshot()
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    (out / "open_source_intelligence.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return data

if __name__ == "__main__":
    print(json.dumps(write_snapshot(), indent=2, ensure_ascii=False))
