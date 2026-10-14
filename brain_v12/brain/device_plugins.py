"""Typed, offline-first device/plugin contract for Brain Hybrid ASIC.

Defines a strict allowlist and read-only interface only; it performs no network
I/O, does not start workloads, and never grants physical-attestation status.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Mapping, Any, Iterable

PLUGIN_API_VERSION = "1.0"
ALLOWED_DEVICE_KINDS = frozenset({"SIMULATOR", "FPGA", "HOSTED_ASIC", "ASIC_DEVICE"})
ALLOWED_CAPABILITIES = frozenset({"read_only_diagnostics", "device_identity", "signed_challenge"})

@dataclass(frozen=True)
class DeviceDescriptor:
    plugin_id: str
    api_version: str
    device_kind: str
    capabilities: frozenset[str]
    display_name: str

@dataclass(frozen=True)
class DiagnosticResult:
    ok: bool
    device_id: str | None
    observed_at_utc: str | None
    payload: Mapping[str, Any]
    source_kind: str

class DevicePlugin(Protocol):
    descriptor: DeviceDescriptor
    def diagnose_read_only(self, *, timeout_seconds: float = 5.0) -> DiagnosticResult: ...

class PluginValidationError(ValueError):
    pass

def validate_descriptor(descriptor: DeviceDescriptor) -> None:
    if not isinstance(descriptor, DeviceDescriptor):
        raise PluginValidationError("DESCRIPTOR_TYPE_REQUIRED")
    for field_name in ("plugin_id", "api_version", "display_name"):
        value = getattr(descriptor, field_name)
        if not isinstance(value, str) or not value.strip():
            raise PluginValidationError(f"{field_name.upper()}_REQUIRED")
    if descriptor.api_version != PLUGIN_API_VERSION:
        raise PluginValidationError("PLUGIN_API_VERSION_UNSUPPORTED")
    if descriptor.device_kind not in ALLOWED_DEVICE_KINDS:
        raise PluginValidationError("DEVICE_KIND_NOT_ALLOWED")
    if not isinstance(descriptor.capabilities, frozenset):
        raise PluginValidationError("CAPABILITIES_MUST_BE_FROZEN_SET")
    unknown = descriptor.capabilities - ALLOWED_CAPABILITIES
    if unknown:
        raise PluginValidationError("UNKNOWN_CAPABILITIES:" + ",".join(sorted(unknown)))
    if descriptor.device_kind == "SIMULATOR" and "signed_challenge" in descriptor.capabilities:
        raise PluginValidationError("SIMULATOR_CANNOT_CLAIM_HARDWARE_ATTESTATION")

class PluginRegistry:
    """Explicit plugin allowlist; registration is not proof of physical hardware."""
    def __init__(self, allowed_plugin_ids: Iterable[str] = ()) -> None:
        self._allowed = frozenset(x for x in allowed_plugin_ids if isinstance(x, str) and x.strip())
        self._plugins: dict[str, DevicePlugin] = {}

    def register(self, plugin: DevicePlugin) -> None:
        descriptor = getattr(plugin, "descriptor", None)
        validate_descriptor(descriptor)
        if descriptor.plugin_id not in self._allowed:
            raise PluginValidationError("PLUGIN_ID_NOT_ALLOWLISTED")
        if descriptor.plugin_id in self._plugins:
            raise PluginValidationError("DUPLICATE_PLUGIN_ID")
        if not callable(getattr(plugin, "diagnose_read_only", None)):
            raise PluginValidationError("READ_ONLY_DIAGNOSTIC_REQUIRED")
        self._plugins[descriptor.plugin_id] = plugin

    def get(self, plugin_id: str) -> DevicePlugin:
        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise PluginValidationError("PLUGIN_NOT_REGISTERED") from exc

    def list_descriptors(self) -> tuple[DeviceDescriptor, ...]:
        return tuple(self._plugins[key].descriptor for key in sorted(self._plugins))
