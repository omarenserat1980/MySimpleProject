from __future__ import annotations

import pytest

from brain_v12.brain.windows_cloud_provider_factory import (
    build_windows_cloud_provider,
    windows_cloud_provider_readiness,
)


def test_factory_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRAIN_WINDOWS_CLOUD_PROVIDER", raising=False)
    assert build_windows_cloud_provider() is None
    assert windows_cloud_provider_readiness()["ready"] is False


def test_factory_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAIN_WINDOWS_CLOUD_PROVIDER", "unknown")
    with pytest.raises(RuntimeError, match="UNSUPPORTED_WINDOWS_CLOUD_PROVIDER"):
        build_windows_cloud_provider()


def test_factory_supports_opennebula_when_cli_is_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAIN_WINDOWS_CLOUD_PROVIDER", "opennebula")

    class ReadyProvider:
        name = "opennebula"

        def readiness(self):
            return {"ready": True, "provider": self.name}

    monkeypatch.setattr(
        "brain_v12.brain.windows_cloud_provider_factory.OpenNebulaWindowsCloudProvider",
        ReadyProvider,
    )
    provider = build_windows_cloud_provider()
    assert provider is not None
    assert provider.name == "opennebula"
