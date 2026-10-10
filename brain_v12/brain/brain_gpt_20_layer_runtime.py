"""Runtime readiness diagnostics for the Brain GPT 20-layer architecture.

Diagnostics are read-only: they report which existing capabilities are wired
without executing a user request or claiming that placeholders are operational.
"""
from __future__ import annotations

from typing import Any

from .brain_gpt_20_layer_pipeline import LAYERS


def _state(status: str, detail: str) -> dict[str, str]:
    return {"status": status, "detail": detail}


def build_layer_runtime_status(brain_ai: Any, session_store: Any = None) -> dict[str, Any]:
    """Describe real integration coverage; READY requires all layers to be ready."""
    router = getattr(brain_ai, "model_router", None)
    provider_status = getattr(brain_ai, "provider", None)
    tools = getattr(brain_ai, "tools", None)
    memory_store = getattr(brain_ai, "memory_store", None)
    cognitive = getattr(brain_ai, "cognitive", None)

    states = {
        "input_gateway": _state("READY", "Brain AI HTTP request model validates input."),
        "identity_access": _state("NOT_WIRED", "No authenticated identity/scope adapter is passed to this pipeline."),
        "conversation_manager": _state("READY" if session_store is not None and callable(getattr(session_store, "get", None)) else "NOT_WIRED",
                                       "Persistent session store is available." if session_store is not None else "Session store was not injected."),
        "context_builder": _state("READY" if session_store is not None and callable(getattr(session_store, "context_messages", None)) else "NOT_WIRED",
                                  "Per-session context reader is available." if session_store is not None else "No per-session context store injected."),
        "memory_retrieval": _state("READY" if memory_store is not None or (session_store is not None and callable(getattr(session_store, "get_memory", None))) else "NOT_WIRED",
                                   "At least one existing Brain memory adapter is available." if memory_store is not None or session_store is not None else "No memory adapter detected."),
        "knowledge_retrieval": _state("NOT_WIRED", "No general file/knowledge retrieval adapter is connected to the 20-layer runtime."),
        "intent_router": _state("READY" if callable(getattr(brain_ai, "_tool_intents", None)) else "NOT_WIRED",
                                "Brain AI tool-intent normalizer is available."),
        "task_planner": _state("NOT_WIRED", "A structured task-plan contract is not yet connected to this runtime."),
        "model_router": _state("READY" if router is not None and callable(getattr(router, "select", None)) else ("PARTIAL" if provider_status is not None else "NOT_WIRED"),
                               "ModelRouter selection/fallback is available." if router is not None else "Only the default provider is available or no router was detected."),
        "reasoning_adapter": _state("READY" if callable(getattr(brain_ai, "chat", None)) else "NOT_WIRED",
                                    "Existing Brain AI reasoning facade is available; its governed tool loop remains responsible for execution."),
        "response_guard": _state("PARTIAL", "Structured BrainAIResponse and error states exist; a dedicated 20-layer output guard is not wired."),
        "tool_planner": _state("READY" if isinstance(tools, dict) and callable(getattr(brain_ai, "_tool_intents", None)) else "NOT_WIRED",
                               "Registered tool catalog and tool-intent normalization are available."),
        "permission_gate": _state("READY" if callable(getattr(brain_ai, "execute_tool", None)) and cognitive is not None else "PARTIAL",
                                  "Existing tool execution checks risk and available permission grants; identity-scoped policy is not connected here."),
        "execution_dispatcher": _state("READY" if callable(getattr(brain_ai, "execute_tool", None)) else "NOT_WIRED",
                                       "Existing governed BrainAI.execute_tool dispatcher is available."),
        "result_collector": _state("READY", "BrainAIResponse carries tool results and evidence."),
        "verification_gate": _state("READY" if callable(getattr(brain_ai, "_verify_tool_outcome", None)) else "NOT_WIRED",
                                    "Existing tool outcome verifier is available; objective-level verification remains tool-specific."),
        "recovery_controller": _state("READY" if callable(getattr(brain_ai, "_diagnose_and_repair", None)) else "NOT_WIRED",
                                      "Existing bounded retry/diagnose-repair functions are available."),
        "audit_evidence": _state("PARTIAL", "Per-response evidence exists; a durable audit sink dedicated to all 20-layer transitions is not wired."),
        "memory_consolidation": _state("PARTIAL" if session_store is not None and callable(getattr(session_store, "set_memory", None)) else "NOT_WIRED",
                                       "Session summary persistence is available." if session_store is not None else "No session memory writer injected."),
        "response_delivery": _state("READY", "Existing Brain AI HTTP response adapter is available."),
    }

    layers = []
    for spec in LAYERS:
        item = states[spec.key]
        layers.append({
            "number": spec.number,
            "key": spec.key,
            "purpose": spec.purpose,
            "status": item["status"],
            "detail": item["detail"],
        })

    ready_count = sum(item["status"] == "READY" for item in layers)
    wired_count = sum(item["status"] in {"READY", "PARTIAL"} for item in layers)
    all_ready = ready_count == len(LAYERS)
    return {
        "ok": True,
        "name": "Brain GPT 20-Layer Runtime",
        "architecture_layers": len(LAYERS),
        "ready_layers": ready_count,
        "wired_or_partial_layers": wired_count,
        "not_wired_layers": sum(item["status"] == "NOT_WIRED" for item in layers),
        "ready": all_ready,
        "status": "READY" if all_ready else "INTEGRATION_INCOMPLETE",
        "execution_performed": False,
        "layers": layers,
    }
