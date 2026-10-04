"""Brain-wide verification policies.

Policies are conservative: unknown output shapes are rejected rather than
converted into synthetic success.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

VERIFIABLE_CAPABILITIES = (
    "media.render",
    "media.image",
    "media.video_generation",
    "media.audio",
    "document.create",
    "code.execute",
    "ai.reasoning",
    "device.execute",
)


def _artifact(result: Any) -> dict[str, Any]:
    if isinstance(result, (str, Path)):
        from .execution_verifier import ExecutionVerifier
        return ExecutionVerifier.verify_file(str(result))
    if isinstance(result, dict):
        for key in ("artifact", "artifact_path", "output_path", "file", "path"):
            value = result.get(key)
            if isinstance(value, (str, Path)):
                from .execution_verifier import ExecutionVerifier
                checked = ExecutionVerifier.verify_file(str(value))
                return {**checked, "result_keys": sorted(result)}
    return {"verified": False, "checks": ("NO_REAL_ARTIFACT_REFERENCE",)}


def verify_capability(capability: str, result: Any) -> dict[str, Any]:
    """Return evidence for a capability without assuming success."""
    artifact_capabilities = {
        "media.render", "media.image", "media.video_generation",
        "media.audio", "document.create", "code.execute",
    }
    if capability in artifact_capabilities:
        return _artifact(result)

    if capability == "ai.reasoning":
        if isinstance(result, str) and result.strip():
            return {"verified": True, "checks": ("NON_EMPTY_REASONING_OUTPUT",)}
        if isinstance(result, dict) and result:
            return {"verified": True, "checks": ("NON_EMPTY_REASONING_RESULT",)}
        return {"verified": False, "checks": ("EMPTY_REASONING_OUTPUT",)}

    if capability == "device.execute":
        if isinstance(result, dict) and result.get("status") in {"OK", "SUCCESS", "COMPLETED"}:
            return {"verified": True, "checks": ("DEVICE_ACKNOWLEDGED_SUCCESS",)}
        return {"verified": False, "checks": ("DEVICE_SUCCESS_NOT_CONFIRMED",)}

    if capability.startswith("publish."):
        if isinstance(result, dict) and result.get("published") is True and result.get("remote_id"):
            return {"verified": True, "checks": ("REMOTE_PUBLISH_CONFIRMED",)}
        return {"verified": False, "checks": ("REMOTE_PUBLISH_NOT_CONFIRMED",)}

    return {"verified": False, "checks": ("NO_VERIFICATION_POLICY",)}


def register_default_verifiers(verifier: Any) -> Any:
    """Install conservative policy-backed verifiers without overwriting custom ones."""
    for capability in VERIFIABLE_CAPABILITIES:
        if not verifier.has_verifier(capability):
            verifier.register(
                capability,
                lambda result, capability=capability: verify_capability(capability, result),
            )
    return verifier
