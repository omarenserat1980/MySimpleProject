"""Preliminary software-node fabric for every cataloged device component.

This is an inventory/lifecycle layer that composes the existing virtual hardware
models. It does not duplicate CPU, RAM, storage, PCIe, network, or mining engines.
Every node is software-only; CATALOGED means an identity exists, not that a device
is fully emulated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .device_catalog import COMPONENT_CLASSES, DEVICE_FAMILIES
from .network_hardware import NETWORK_DEVICE_KINDS

# Existing implementation adapters. "partial" means a reusable model exists, not
# complete compatibility with every commercial SKU or its proprietary firmware.
MODEL_BINDINGS = {
    "cpu": ("VirtualCPU", "partial"),
    "gpu": ("VirtualGPU", "partial"),
    "ram": ("VirtualRAM", "partial"),
    "cache": ("MemoryTimingModel", "partial"),
    "storage": ("VirtualStorage/VirtualDisk", "partial"),
    "storage_controller": ("storage_profiles", "catalog_or_contract"),
    "network_nic": ("VirtualNIC/VirtualNetworkFabric", "partial"),
    "pcie": ("VirtualPCIeFabric", "transaction_level"),
    "battery": ("VirtualBattery", "estimate"),
    "power": ("PowerThermalModel", "estimate"),
    "thermal": ("PowerThermalModel/VirtualBMC", "estimate"),
    "security": ("VirtualTPM", "software_contract"),
    "clock_rtc": ("VirtualWatchdog", "partial"),
    "usb": ("VirtualUSBController", "partial"),
    "radio_modem": ("VirtualModem", "isolated_state_only"),
    "i2c_spi_gpio": ("VirtualPeripheralFabric", "state_or_contract"),
    "enclosure": ("device_catalog", "inventory_only"),
    "satellite_comms": ("network_hardware", "state_or_estimate"),
}

@dataclass
class SoftwareHardwareNode:
    node_id: str
    node_type: str
    family_id: str
    component_id: str
    component_name: str
    model_binding: str
    fidelity: str
    state: str = "CATALOGED"
    enabled: bool = True
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def status(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "family_id": self.family_id,
            "component_id": self.component_id,
            "component_name": self.component_name,
            "model_binding": self.model_binding,
            "fidelity": self.fidelity,
            "state": self.state,
            "enabled": self.enabled,
            "dependencies": list(self.dependencies),
            "physical_hardware_required": False,
            "external_io_enabled": False,
            "full_device_emulation_claimed": False,
        }

class SoftwareHardwareNodeFabric:
    """Build a stable software node for every family/component pair and network kind."""

    def __init__(self) -> None:
        self.nodes: dict[str, SoftwareHardwareNode] = {}
        self._build_catalog_nodes()

    @staticmethod
    def _safe_id(value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")

    def _build_catalog_nodes(self) -> None:
        for family_id, family in sorted(DEVICE_FAMILIES.items()):
            for component_id in sorted(set(family["components"])):
                definition = COMPONENT_CLASSES[component_id]
                binding, fidelity = MODEL_BINDINGS.get(
                    component_id, ("catalog_contract", definition[2])
                )
                node_id = f"device.{family_id}.{component_id}"
                self.nodes[node_id] = SoftwareHardwareNode(
                    node_id=node_id,
                    node_type="component",
                    family_id=family_id,
                    component_id=component_id,
                    component_name=definition[0],
                    model_binding=binding,
                    fidelity=fidelity,
                    metadata={"category": family["category"], "examples": list(family["examples"])},
                )
        # Each network-device class gets its own reusable software node template.
        for kind, description in sorted(NETWORK_DEVICE_KINDS.items()):
            node_id = f"network.{kind}"
            self.nodes[node_id] = SoftwareHardwareNode(
                node_id=node_id,
                node_type="network_device",
                family_id="networking",
                component_id=kind,
                component_name=description,
                model_binding="VirtualNetworkFabric/NetworkDevice",
                fidelity="logical_simulation",
                metadata={"kind": kind},
            )

    def get_node(self, node_id: str) -> dict:
        if node_id not in self.nodes:
            raise KeyError("SOFTWARE_HARDWARE_NODE_UNKNOWN")
        return self.nodes[node_id].status()

    def set_enabled(self, node_id: str, enabled: bool) -> dict:
        if node_id not in self.nodes:
            raise KeyError("SOFTWARE_HARDWARE_NODE_UNKNOWN")
        node = self.nodes[node_id]
        node.enabled = bool(enabled)
        node.state = "READY" if node.enabled else "DISABLED"
        return node.status()

    def set_dependencies(self, node_id: str, dependencies: list[str]) -> dict:
        if node_id not in self.nodes or any(dep not in self.nodes for dep in dependencies):
            raise ValueError("SOFTWARE_HARDWARE_DEPENDENCY_UNKNOWN")
        if node_id in dependencies:
            raise ValueError("SOFTWARE_HARDWARE_SELF_DEPENDENCY")
        node = self.nodes[node_id]
        node.dependencies = sorted(set(dependencies))
        return node.status()

    def inventory(self) -> dict:
        counts: dict[str, int] = {}
        for node in self.nodes.values():
            counts[node.node_type] = counts.get(node.node_type, 0) + 1
        return {
            "schema_version": 1,
            "mode": "SOFTWARE_ONLY",
            "physical_hardware_required": False,
            "external_io_enabled": False,
            "family_count": len(DEVICE_FAMILIES),
            "component_class_count": len(COMPONENT_CLASSES),
            "network_device_kind_count": len(NETWORK_DEVICE_KINDS),
            "software_node_count": len(self.nodes),
            "node_counts_by_type": counts,
            "nodes": [node.status() for _, node in sorted(self.nodes.items())],
            "limitations": [
                "Inventory nodes are not equivalent to fully emulated devices.",
                "Commercial SKUs and proprietary firmware require separate documented profiles.",
                "Power, thermal, timing, radio and performance metrics may be estimates.",
                "This fabric never opens host devices or external network connections.",
            ],
        }

    def validate(self) -> dict:
        duplicate_ids = len(self.nodes) != len(set(self.nodes))
        invalid_dependencies = [
            node.node_id for node in self.nodes.values()
            if any(dep not in self.nodes for dep in node.dependencies)
        ]
        return {
            "ok": not duplicate_ids and not invalid_dependencies,
            "software_node_count": len(self.nodes),
            "duplicate_ids": duplicate_ids,
            "invalid_dependency_nodes": invalid_dependencies,
            "physical_hardware_required": False,
        }
