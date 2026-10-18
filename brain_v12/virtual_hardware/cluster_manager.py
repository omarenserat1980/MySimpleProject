"""Simulation-only cluster manager for Brain virtual hosts.

The manager models placement and failover decisions in memory. It does not
provision cloud instances, open network sockets, or claim physical capacity.
"""
from __future__ import annotations

from .virtual_host import BrainVirtualHost


class BrainVirtualClusterManager:
    """Manage named virtual hosts with deterministic round-robin placement."""

    def __init__(self, cluster_id: str = "brain-virtual-cluster-v1",
                 ram_cells_per_task: int = 65536, clock_width_bits: int = 32):
        if not isinstance(cluster_id, str) or not cluster_id.strip():
            raise ValueError("CLUSTER_ID_REQUIRED")
        if (not isinstance(ram_cells_per_task, int) or isinstance(ram_cells_per_task, bool)
                or ram_cells_per_task <= 0):
            raise ValueError("CLUSTER_RAM_CELLS_MUST_BE_POSITIVE")
        if (not isinstance(clock_width_bits, int) or isinstance(clock_width_bits, bool)
                or clock_width_bits <= 0):
            raise ValueError("CLUSTER_CLOCK_WIDTH_MUST_BE_POSITIVE")
        self.cluster_id = cluster_id.strip()
        self.ram_cells_per_task = ram_cells_per_task
        self.clock_width_bits = clock_width_bits
        self.nodes: dict[str, dict] = {}
        self.events: list[dict] = []
        self._cursor = 0

    def add_node(self, node_id: str) -> dict:
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("CLUSTER_NODE_ID_REQUIRED")
        node_id = node_id.strip()
        if node_id in self.nodes:
            raise ValueError("CLUSTER_NODE_ALREADY_EXISTS")
        host = BrainVirtualHost(
            host_id=f"{self.cluster_id}:{node_id}",
            ram_cells_per_task=self.ram_cells_per_task,
            clock_width_bits=self.clock_width_bits,
        )
        self.nodes[node_id] = {"host": host, "state": "READY"}
        self._event("NODE_ADDED", node_id=node_id)
        return self.node_status(node_id)

    def set_node_state(self, node_id: str, state: str) -> dict:
        node = self._get_node(node_id)
        if state not in {"READY", "DRAINING", "FAILED"}:
            raise ValueError("CLUSTER_NODE_STATE_INVALID")
        previous = node["state"]
        node["state"] = state
        self._event("NODE_STATE_CHANGED", node_id=node_id, previous=previous, state=state)
        return self.node_status(node_id)

    def place_task(self, name: str, program) -> dict:
        candidates = [
            node_id for node_id, node in self.nodes.items()
            if node["state"] == "READY"
        ]
        if not candidates:
            raise RuntimeError("CLUSTER_NO_READY_NODES")
        self._cursor %= len(candidates)
        node_id = candidates[self._cursor]
        self._cursor = (self._cursor + 1) % len(candidates)
        pid = self.nodes[node_id]["host"].create_task(name, program)
        self._event("TASK_PLACED", node_id=node_id, name=name, pid=pid)
        return {"ok": True, "mode": "SIMULATED_CLUSTER_PLACEMENT",
                "cluster_id": self.cluster_id, "node_id": node_id, "pid": pid,
                "physical_hardware": False}

    def run_node(self, node_id: str, max_ticks: int = 10000) -> dict:
        node = self._get_node(node_id)
        if node["state"] != "READY":
            raise RuntimeError("CLUSTER_NODE_NOT_READY")
        result = node["host"].run_tasks(max_ticks=max_ticks)
        self._event("NODE_TASKS_RUN", node_id=node_id,
                    ticks=result["ticks_this_run"], completed=result["completed"])
        return result

    def node_status(self, node_id: str) -> dict:
        node = self._get_node(node_id)
        health = node["host"].health()
        return {"node_id": node_id, "state": node["state"],
                "health": health, "physical_hardware": False}

    def health(self) -> dict:
        statuses = [self.node_status(node_id) for node_id in self.nodes]
        ready = sum(node["state"] == "READY" and node["health"]["ok"] for node in statuses)
        failed = sum(node["state"] == "FAILED" or not node["health"]["ok"] for node in statuses)
        return {
            "ok": bool(statuses) and ready > 0,
            "mode": "SIMULATED_BRAIN_VIRTUAL_CLUSTER",
            "cluster_id": self.cluster_id,
            "node_count": len(statuses),
            "ready_nodes": ready,
            "failed_nodes": failed,
            "nodes": statuses,
            "event_count": len(self.events),
            "cloud_resources_provisioned": False,
            "network_listener_enabled": False,
            "physical_hardware": False,
        }

    def checkpoint(self) -> dict:
        return {
            "schema": "brain-virtual-cluster-checkpoint-v1",
            "mode": "SIMULATED_BRAIN_VIRTUAL_CLUSTER",
            "cluster_id": self.cluster_id,
            "ram_cells_per_task": self.ram_cells_per_task,
            "clock_width_bits": self.clock_width_bits,
            "cursor": self._cursor,
            "nodes": [
                {"node_id": node_id, "state": node["state"],
                 "host": node["host"].checkpoint()}
                for node_id, node in self.nodes.items()
            ],
            "events": [dict(event) for event in self.events],
            "physical_hardware": False,
        }

    def restore_checkpoint(self, checkpoint: dict) -> dict:
        if (not isinstance(checkpoint, dict)
                or checkpoint.get("schema") != "brain-virtual-cluster-checkpoint-v1"):
            raise ValueError("CLUSTER_CHECKPOINT_SCHEMA_UNSUPPORTED")
        if checkpoint.get("mode") != "SIMULATED_BRAIN_VIRTUAL_CLUSTER":
            raise ValueError("CLUSTER_CHECKPOINT_MODE_INVALID")
        try:
            cluster_id = checkpoint["cluster_id"]
            ram = checkpoint["ram_cells_per_task"]
            width = checkpoint["clock_width_bits"]
            cursor = checkpoint["cursor"]
            raw_nodes = checkpoint["nodes"]
            raw_events = checkpoint["events"]
        except (KeyError, TypeError) as exc:
            raise ValueError("CLUSTER_CHECKPOINT_MALFORMED") from exc
        if not isinstance(cluster_id, str) or not cluster_id.strip():
            raise ValueError("CLUSTER_CHECKPOINT_ID_INVALID")
        for value, label, minimum in ((ram, "RAM", 1), (width, "CLOCK", 1), (cursor, "CURSOR", 0)):
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                raise ValueError(f"CLUSTER_CHECKPOINT_{label}_INVALID")
        if not isinstance(raw_nodes, list) or not isinstance(raw_events, list):
            raise ValueError("CLUSTER_CHECKPOINT_COLLECTION_INVALID")
        candidate_nodes = {}
        for item in raw_nodes:
            if not isinstance(item, dict):
                raise ValueError("CLUSTER_CHECKPOINT_NODE_INVALID")
            node_id, state, host_snapshot = item.get("node_id"), item.get("state"), item.get("host")
            if not isinstance(node_id, str) or not node_id.strip() or node_id in candidate_nodes:
                raise ValueError("CLUSTER_CHECKPOINT_NODE_ID_INVALID")
            if state not in {"READY", "DRAINING", "FAILED"}:
                raise ValueError("CLUSTER_CHECKPOINT_NODE_STATE_INVALID")
            host = BrainVirtualHost(
                host_id=f"{cluster_id.strip()}:{node_id}",
                ram_cells_per_task=ram, clock_width_bits=width,
            )
            host.restore_checkpoint(host_snapshot)
            candidate_nodes[node_id] = {"host": host, "state": state}
        candidate_events = []
        for event in raw_events:
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise ValueError("CLUSTER_CHECKPOINT_EVENT_INVALID")
            candidate_events.append(dict(event))
        self.cluster_id = cluster_id.strip()
        self.ram_cells_per_task = ram
        self.clock_width_bits = width
        self._cursor = cursor
        self.nodes = candidate_nodes
        self.events = candidate_events
        return self.health()

    def _get_node(self, node_id: str) -> dict:
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError("CLUSTER_NODE_NOT_FOUND")
        return node

    def _event(self, event_type: str, **details) -> None:
        self.events.append({"type": event_type, **details})
