"""Governed 20-layer architecture contract for Brain GPT.

This module defines orchestration contracts only. It does not pretend that a
layer is operational until an application explicitly registers its handler.
Handlers should be deterministic adapters around existing Brain capabilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class LayerSpec:
    number: int
    key: str
    purpose: str
    required: bool = True


LAYERS: tuple[LayerSpec, ...] = (
    LayerSpec(1, "input_gateway", "Normalize user input and request metadata."),
    LayerSpec(2, "identity_access", "Validate identity, scope, and access policy."),
    LayerSpec(3, "conversation_manager", "Resolve session and conversation state."),
    LayerSpec(4, "context_builder", "Assemble bounded, relevant conversation context."),
    LayerSpec(5, "memory_retrieval", "Retrieve permitted persistent memories."),
    LayerSpec(6, "knowledge_retrieval", "Retrieve available files and trusted knowledge."),
    LayerSpec(7, "intent_router", "Classify intent and task category."),
    LayerSpec(8, "task_planner", "Build a bounded plan and completion criteria."),
    LayerSpec(9, "model_router", "Select an available model and permitted fallback."),
    LayerSpec(10, "reasoning_adapter", "Invoke the selected model for analysis or generation."),
    LayerSpec(11, "response_guard", "Check output shape, uncertainty, and policy constraints."),
    LayerSpec(12, "tool_planner", "Choose only registered tools with validated arguments."),
    LayerSpec(13, "permission_gate", "Require approval for protected actions."),
    LayerSpec(14, "execution_dispatcher", "Dispatch approved work to existing Brain executors."),
    LayerSpec(15, "result_collector", "Collect tool outputs and execution metadata."),
    LayerSpec(16, "verification_gate", "Verify outcomes against explicit success criteria."),
    LayerSpec(17, "recovery_controller", "Bound retries and propose safe recovery actions."),
    LayerSpec(18, "audit_evidence", "Record provenance, decisions, and evidence references."),
    LayerSpec(19, "memory_consolidation", "Persist only eligible session outcomes and summaries."),
    LayerSpec(20, "response_delivery", "Return the answer with status and evidence disclosure."),
)


@dataclass
class LayerOutcome:
    layer: str
    status: str
    output: dict[str, Any]
    error: str | None = None


LayerHandler = Callable[[dict[str, Any]], dict[str, Any]]


class BrainGPT20LayerPipeline:
    """Fail-closed, sequential orchestration over explicitly registered handlers."""

    def __init__(self, handlers: dict[str, LayerHandler] | None = None):
        self.handlers: dict[str, LayerHandler] = dict(handlers or {})

    @staticmethod
    def layer_specs() -> list[dict[str, Any]]:
        return [
            {"number": layer.number, "key": layer.key, "purpose": layer.purpose,
             "required": layer.required}
            for layer in LAYERS
        ]

    def register(self, layer_key: str, handler: LayerHandler) -> None:
        if layer_key not in {layer.key for layer in LAYERS}:
            raise ValueError("UNKNOWN_BRAIN_GPT_LAYER")
        if not callable(handler):
            raise TypeError("LAYER_HANDLER_MUST_BE_CALLABLE")
        self.handlers[layer_key] = handler

    def status(self) -> dict[str, Any]:
        configured = [layer.key for layer in LAYERS if layer.key in self.handlers]
        missing = [layer.key for layer in LAYERS if layer.required and layer.key not in self.handlers]
        return {
            "name": "Brain GPT 20-Layer Pipeline",
            "layer_count": len(LAYERS),
            "configured_count": len(configured),
            "configured_layers": configured,
            "missing_required_layers": missing,
            "ready": not missing,
            "status": "READY" if not missing else "NOT_CONFIGURED",
        }

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            return {"ok": False, "status": "INVALID_REQUEST", "outcomes": []}

        state: dict[str, Any] = {"request": dict(request), "layer_outputs": {}}
        outcomes: list[LayerOutcome] = []

        missing = [layer.key for layer in LAYERS if layer.required and layer.key not in self.handlers]
        if missing:
            return {
                "ok": False,
                "status": "PIPELINE_NOT_CONFIGURED",
                "missing_required_layers": missing,
                "outcomes": [],
                "evidence": {"type": "configuration_check", "required_layer_count": len(LAYERS)},
            }

        for layer in LAYERS:
            try:
                result = self.handlers[layer.key](dict(state))
                if not isinstance(result, dict):
                    raise TypeError("LAYER_OUTPUT_MUST_BE_A_DICT")
                if result.get("ok") is False:
                    outcome = LayerOutcome(layer.key, "FAILED", result, str(result.get("error", "LAYER_REPORTED_FAILURE")))
                    outcomes.append(outcome)
                    return {
                        "ok": False, "status": "LAYER_FAILED", "failed_layer": layer.key,
                        "outcomes": [vars(item) for item in outcomes],
                        "evidence": {"type": "layer_execution", "completed_layers": len(outcomes)},
                    }
                state["layer_outputs"][layer.key] = result
                state["latest_output"] = result
                outcomes.append(LayerOutcome(layer.key, "COMPLETED", result))
            except Exception as exc:
                outcomes.append(LayerOutcome(layer.key, "FAILED", {}, type(exc).__name__))
                return {
                    "ok": False, "status": "LAYER_EXCEPTION", "failed_layer": layer.key,
                    "outcomes": [vars(item) for item in outcomes],
                    "evidence": {"type": "layer_execution", "completed_layers": len(outcomes)},
                }

        return {
            "ok": True, "status": "COMPLETED", "output": state.get("latest_output", {}),
            "outcomes": [vars(item) for item in outcomes],
            "evidence": {
                "type": "layer_execution", "completed_layers": len(outcomes),
                "ordered_layers": [item.key for item in LAYERS],
            },
        }
