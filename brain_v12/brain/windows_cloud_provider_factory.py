from __future__ import annotations

"""Safe construction of the configured Windows Cloud provider."""

import os
from typing import Any

from .terraform_windows_cloud_provider import TerraformWindowsCloudProvider
from .windows_cloud_executor import WindowsCloudProvider


def build_windows_cloud_provider() -> WindowsCloudProvider | None:
    """Return a real provider adapter only when explicitly configured."""
    backend = os.environ.get("BRAIN_WINDOWS_CLOUD_PROVIDER", "").strip().lower()
    if backend in {"", "none", "disabled"}:
        return None
    if backend == "terraform":
        provider = TerraformWindowsCloudProvider()
        if provider.readiness()["ready"]:
            return provider
        return None
    raise RuntimeError(f"UNSUPPORTED_WINDOWS_CLOUD_PROVIDER:{backend}")


def windows_cloud_provider_readiness() -> dict[str, Any]:
    backend = os.environ.get("BRAIN_WINDOWS_CLOUD_PROVIDER", "").strip().lower()
    if backend in {"", "none", "disabled"}:
        return {"ready": False, "provider": None, "reason": "CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED"}
    if backend == "terraform":
        return TerraformWindowsCloudProvider().readiness()
    return {"ready": False, "provider": backend, "reason": "UNSUPPORTED_WINDOWS_CLOUD_PROVIDER"}
