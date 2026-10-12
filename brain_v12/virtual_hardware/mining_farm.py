"""Software-only mining-farm topology and deterministic telemetry aggregation.

No real mining, pool connectivity, wallet operations, or physical-device control.
All energy/hash values are estimates inherited from generic ASIC profiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .mining_hardware import ASICProfile, DEFAULT_ASIC_PROFILES, VirtualASICMiner


@dataclass
class FarmNode:
    node_id: str
    miner: VirtualASICMiner
    rack_id: str
    network_segment: str
    enabled: bool = True
    elapsed_seconds: float = 0.0
    estimated_energy_wh: float = 0.0
    last_snapshot: dict[str, Any] = field(default_factory=dict)


class VirtualMiningFarm:
    """Small deterministic inventory of simulated ASIC miners and racks."""

    def __init__(self, farm_id: str = "brain-mining-farm") -> None:
        if not farm_id.strip():
            raise ValueError("farm_id is required")
        self.farm_id = farm_id
        self.nodes: dict[str, FarmNode] = {}
        self.simulated_pool = {"connected": False, "endpoint": None, "job_id": None}
        self.events: list[dict[str, Any]] = []

    def add_miner(
        self,
        node_id: str,
        *,
        profile: ASICProfile | None = None,
        rack_id: str = "rack-01",
        network_segment: str = "isolated-sim-net",
    ) -> dict[str, Any]:
        if not node_id.strip() or node_id in self.nodes:
            raise ValueError("node_id must be non-empty and unique")
        if not rack_id.strip() or not network_segment.strip():
            raise ValueError("rack_id and network_segment are required")
        node = FarmNode(node_id, VirtualASICMiner(profile or DEFAULT_ASIC_PROFILES["asic_midrange"]),
                        rack_id, network_segment)
        self.nodes[node_id] = node
        self.events.append({"event": "miner_added", "node_id": node_id, "rack_id": rack_id})
        return self.node_status(node_id)

    def start_all(self) -> dict[str, Any]:
        for node in self.nodes.values():
            if node.enabled:
                node.last_snapshot = node.miner.start()
        return self.snapshot()

    def stop_all(self) -> dict[str, Any]:
        for node in self.nodes.values():
            node.last_snapshot = node.miner.stop()
        self.simulated_pool.update({"connected": False, "endpoint": None, "job_id": None})
        return self.snapshot()

    def assign_simulated_job(self, job_id: str, *, endpoint_label: str = "synthetic-pool") -> dict[str, Any]:
        """Assign a local test label only; deliberately never opens a network connection."""
        if not job_id.strip() or not endpoint_label.strip():
            raise ValueError("job_id and endpoint_label are required")
        active = [n for n in self.nodes.values()
                  if n.enabled and n.miner.data.state.value in {"mining_simulated", "throttled"}]
        if not active:
            raise RuntimeError("no active simulated miners")
        self.simulated_pool.update({"connected": True, "endpoint": endpoint_label, "job_id": job_id})
        self.events.append({"event": "simulated_job_assigned", "job_id": job_id, "workers": len(active)})
        return {"farm_id": self.farm_id, "simulated_pool": dict(self.simulated_pool),
                "workers": [n.node_id for n in active], "external_network_used": False}

    def tick(self, seconds: float = 1.0, *, inlet_temperature_c: float | None = None) -> dict[str, Any]:
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        for node in self.nodes.values():
            if not node.enabled:
                continue
            before = node.miner.data.estimated_power_w
            snap = node.miner.tick(seconds, inlet_temperature_c=inlet_temperature_c)
            node.last_snapshot = snap
            node.elapsed_seconds += seconds
            # Trapezoidal integration: W * s / 3600 = Wh.
            node.estimated_energy_wh += ((before + snap["estimated"]["power_w"]) / 2.0) * seconds / 3600.0
        return self.snapshot()

    def set_node_enabled(self, node_id: str, enabled: bool) -> dict[str, Any]:
        node = self.nodes[node_id]
        node.enabled = bool(enabled)
        if not node.enabled:
            node.last_snapshot = node.miner.stop()
        self.events.append({"event": "node_enabled" if enabled else "node_disabled", "node_id": node_id})
        return self.node_status(node_id)

    def node_status(self, node_id: str) -> dict[str, Any]:
        node = self.nodes[node_id]
        snap = node.miner.snapshot()
        return {"node_id": node.node_id, "rack_id": node.rack_id,
                "network_segment": node.network_segment, "enabled": node.enabled,
                "elapsed_seconds": node.elapsed_seconds,
                "estimated_energy_wh": round(node.estimated_energy_wh, 6),
                "miner": snap}

    def snapshot(self) -> dict[str, Any]:
        node_statuses = [self.node_status(node_id) for node_id in sorted(self.nodes)]
        estimated_hash = sum(n["miner"]["estimated"]["hash_rate_th_s"] for n in node_statuses)
        estimated_power = sum(n["miner"]["estimated"]["power_w"] for n in node_statuses)
        estimated_energy = sum(n["estimated_energy_wh"] for n in node_statuses)
        return {
            "farm_id": self.farm_id,
            "node_count": len(node_statuses),
            "enabled_node_count": sum(n["enabled"] for n in node_statuses),
            "active_node_count": sum(n["miner"]["state"] in {"mining_simulated", "throttled"} for n in node_statuses),
            "racks": sorted({n["rack_id"] for n in node_statuses}),
            "estimated": {"hash_rate_th_s": round(estimated_hash, 6),
                          "power_w": round(estimated_power, 3),
                          "energy_wh": round(estimated_energy, 6),
                          "calibrated": False},
            "simulated_pool": dict(self.simulated_pool),
            "external_network_used": False,
            "real_bitcoin_mining": False,
            "nodes": node_statuses,
            "recent_events": self.events[-20:],
            "fidelity": "software_only_farm_orchestration_estimates",
        }
