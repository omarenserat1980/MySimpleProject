"""Per-request evidence trace for the Brain GPT 20-layer architecture.

This observer summarizes the existing Brain AI request path. It does not
execute tools or claim that unwired layers have been implemented.
"""
from __future__ import annotations

from typing import Any

from .brain_gpt_20_layer_pipeline import LAYERS


def build_request_layer_trace(brain_ai: Any, message: str, instructions: str, response: Any) -> dict[str, Any]:
    evidence = list(getattr(response, "evidence", []) or [])
    evidence_types = {item.get("type") for item in evidence if isinstance(item, dict)}
    tool_evidence = [item for item in evidence if isinstance(item, dict) and item.get("type") == "tool"]
    routed = "model_routing" in evidence_types
    provider_called = "provider" in evidence_types
    has_session_context = "[BRAIN_SESSION_CONTEXT]" in (instructions or "")
    has_session_memory = "[BRAIN_SESSION_MEMORY]" in (instructions or "")
    memory_available = getattr(brain_ai, "memory_store", None) is not None or has_session_memory
    self_healing = bool(evidence_types & {"self_healing", "diagnose_repair"})
    verified_tools = bool(tool_evidence) and all(item.get("verified") is True for item in tool_evidence)
    approval_blocked = getattr(response, "mode", "") == "approval"

    statuses = {
        "input_gateway": ("COMPLETED" if (message or "").strip() else "FAILED", "The Brain AI facade received a non-empty request." if (message or "").strip() else "Empty request."),
        "identity_access": ("NOT_WIRED", "Identity and account-scoped authorization are not enforced by this facade itself."),
        "conversation_manager": ("COMPLETED" if has_session_context or has_session_memory else "NOT_IN_SCOPE", "Session context was supplied by the persistent chat API." if has_session_context or has_session_memory else "This request did not include persistent session markers."),
        "context_builder": ("COMPLETED" if getattr(brain_ai, "memory_store", None) is not None or has_session_context else "PARTIAL", "Existing Brain or session context was available." if getattr(brain_ai, "memory_store", None) is not None or has_session_context else "No explicit context adapter was confirmed for this request."),
        "memory_retrieval": ("COMPLETED" if memory_available else "PARTIAL", "Brain or session memory is available to the request." if memory_available else "No memory source was confirmed."),
        "knowledge_retrieval": ("NOT_WIRED", "A dedicated trusted-file/knowledge retrieval step is not present in this request path."),
        "intent_router": ("COMPLETED" if provider_called else "PARTIAL", "The model response was normalized for tool intents." if provider_called else "No provider response was recorded."),
        "task_planner": ("NOT_WIRED", "A structured plan with explicit success criteria is not emitted by this request path."),
        "model_router": ("COMPLETED" if routed else ("PARTIAL" if provider_called else "NOT_CONFIRMED"), "Model routing evidence was recorded." if routed else "No successful model-routing evidence was recorded."),
        "reasoning_adapter": ("COMPLETED" if provider_called else "FAILED", "A provider response was recorded." if provider_called else "No provider response was recorded."),
        "response_guard": ("PARTIAL", "A dedicated post-generation policy/output guard is not wired as a distinct layer."),
        "tool_planner": ("COMPLETED" if provider_called else "NOT_TRIGGERED", "The response was checked for registered tool intents." if provider_called else "Model response did not reach intent normalization."),
        "permission_gate": ("COMPLETED" if tool_evidence or approval_blocked else "NOT_TRIGGERED", "Tool execution/approval path was reached." if tool_evidence or approval_blocked else "No tool action was requested."),
        "execution_dispatcher": ("BLOCKED" if approval_blocked else ("COMPLETED" if tool_evidence else "NOT_TRIGGERED"), "Execution stopped at approval." if approval_blocked else ("Tool execution evidence was recorded." if tool_evidence else "No tool execution occurred.")),
        "result_collector": ("COMPLETED" if tool_evidence else "NOT_TRIGGERED", "Tool outcome evidence was collected." if tool_evidence else "No tool result was produced."),
        "verification_gate": ("COMPLETED" if verified_tools else ("PARTIAL" if tool_evidence else "NOT_TRIGGERED"), "All recorded tool outcomes were marked verified." if verified_tools else ("At least one tool outcome is not verified." if tool_evidence else "No tool outcome required verification.")),
        "recovery_controller": ("COMPLETED" if self_healing else "NOT_TRIGGERED", "A retry or diagnose/repair event was recorded." if self_healing else "Recovery was not triggered for this request."),
        "audit_evidence": ("COMPLETED" if evidence else "PARTIAL", "Request evidence is present in the response." if evidence else "No response evidence was recorded."),
        "memory_consolidation": ("NOT_WIRED", "This request path does not automatically consolidate a new long-term/session summary."),
        "response_delivery": ("COMPLETED" if getattr(response, "ok", False) or getattr(response, "error", None) else "FAILED", "The response contains a success or error outcome." if getattr(response, "ok", False) or getattr(response, "error", None) else "No final outcome was recorded."),
    }
    layers = [
        {"number": spec.number, "key": spec.key, "status": statuses[spec.key][0], "detail": statuses[spec.key][1]}
        for spec in LAYERS
    ]
    return {
        "type": "brain_gpt_20_layer_trace",
        "architecture_layers": 20,
        "completed_layers": sum(item["status"] == "COMPLETED" for item in layers),
        "partial_layers": sum(item["status"] == "PARTIAL" for item in layers),
        "not_wired_layers": sum(item["status"] == "NOT_WIRED" for item in layers),
        "execution_performed_by_trace": False,
        "layers": layers,
    }
