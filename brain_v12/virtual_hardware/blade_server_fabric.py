"""Simulation-only blade chassis built on BrainVirtualClusterManager."""
from __future__ import annotations

from .cluster_manager import BrainVirtualClusterManager


class BrainBladeServerFabric:
    """Model a chassis, isolated blades, per-blade state and deterministic placement."""

    VALID_STATES = {"ONLINE", "DRAINING", "FAILED"}

    def __init__(self, fabric_id: str = "brain-blade-fabric-v1",
                 ram_cells_per_task: int = 65536, clock_width_bits: int = 32,
                 task_slots_per_blade: int = 64):
        if not isinstance(fabric_id, str) or not fabric_id.strip():
            raise ValueError("FABRIC_ID_REQUIRED")
        for value, label in ((ram_cells_per_task, "RAM"), (clock_width_bits, "CLOCK"),
                             (task_slots_per_blade, "TASK_SLOTS")):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"FABRIC_{label}_MUST_BE_POSITIVE")
        self.fabric_id = fabric_id.strip()
        self.ram_cells_per_task = ram_cells_per_task
        self.clock_width_bits = clock_width_bits
        self.task_slots_per_blade = task_slots_per_blade
        self.blades: dict[str, dict] = {}
        self.events: list[dict] = []
        self._cursor = 0

    def add_blade(self, blade_id: str, node_count: int = 1) -> dict:
        if not isinstance(blade_id, str) or not blade_id.strip():
            raise ValueError("FABRIC_BLADE_ID_REQUIRED")
        blade_id = blade_id.strip()
        if blade_id in self.blades:
            raise ValueError("FABRIC_BLADE_ALREADY_EXISTS")
        if not isinstance(node_count, int) or isinstance(node_count, bool) or node_count <= 0:
            raise ValueError("FABRIC_NODE_COUNT_MUST_BE_POSITIVE")
        cluster = BrainVirtualClusterManager(
            cluster_id=f"{self.fabric_id}:{blade_id}",
            ram_cells_per_task=self.ram_cells_per_task,
            clock_width_bits=self.clock_width_bits)
        for i in range(node_count):
            cluster.add_node(f"node-{i + 1}")
        self.blades[blade_id] = {"state": "ONLINE", "cluster": cluster}
        self._event("BLADE_ADDED", blade_id=blade_id, node_count=node_count)
        return self.blade_status(blade_id)

    def set_blade_state(self, blade_id: str, state: str) -> dict:
        blade = self._get_blade(blade_id)
        if state not in self.VALID_STATES:
            raise ValueError("FABRIC_BLADE_STATE_INVALID")
        previous = blade["state"]
        blade["state"] = state
        if state == "FAILED":
            for node_id in list(blade["cluster"].nodes):
                blade["cluster"].set_node_state(node_id, "FAILED")
        elif state == "DRAINING":
            for node_id in list(blade["cluster"].nodes):
                if blade["cluster"].nodes[node_id]["state"] == "READY":
                    blade["cluster"].set_node_state(node_id, "DRAINING")
        elif previous in {"FAILED", "DRAINING"}:
            for node_id in list(blade["cluster"].nodes):
                blade["cluster"].set_node_state(node_id, "READY")
        self._event("BLADE_STATE_CHANGED", blade_id=blade_id, previous=previous, state=state)
        return self.blade_status(blade_id)

    def place_task(self, name: str, program) -> dict:
        candidates = []
        for blade_id, blade in self.blades.items():
            if blade["state"] != "ONLINE":
                continue
            used = sum(len(n["host"].tasks._tasks) for n in blade["cluster"].nodes.values())
            if used >= self.task_slots_per_blade:
                continue
            if blade["cluster"].health()["ready_nodes"]:
                candidates.append(blade_id)
        if not candidates:
            raise RuntimeError("FABRIC_NO_CAPACITY")
        self._cursor %= len(candidates)
        blade_id = candidates[self._cursor]
        self._cursor = (self._cursor + 1) % len(candidates)
        result = self.blades[blade_id]["cluster"].place_task(name, program)
        self._event("TASK_PLACED", blade_id=blade_id, node_id=result["node_id"], pid=result["pid"])
        return {"ok": True, "mode": "SIMULATED_BLADE_PLACEMENT",
                "fabric_id": self.fabric_id, "blade_id": blade_id,
                "node_id": result["node_id"], "pid": result["pid"],
                "physical_hardware": False}

    def run_blade(self, blade_id: str, max_ticks: int = 10000) -> dict:
        blade = self._get_blade(blade_id)
        if blade["state"] != "ONLINE":
            raise RuntimeError("FABRIC_BLADE_NOT_ONLINE")
        results = []
        for node_id, node in blade["cluster"].nodes.items():
            if node["state"] == "READY":
                results.append({"node_id": node_id, "result": blade["cluster"].run_node(node_id, max_ticks)})
        self._event("BLADE_RUN", blade_id=blade_id, node_runs=len(results))
        return {"blade_id": blade_id, "node_runs": results, "mode": "SIMULATED_BLADE_RUN"}

    def blade_status(self, blade_id: str) -> dict:
        blade = self._get_blade(blade_id)
        return {"blade_id": blade_id, "state": blade["state"],
                "cluster_health": blade["cluster"].health(),
                "task_slots": self.task_slots_per_blade,
                "tasks_registered": sum(len(n["host"].tasks._tasks) for n in blade["cluster"].nodes.values()),
                "physical_hardware": False}

    def health(self) -> dict:
        statuses = [self.blade_status(bid) for bid in self.blades]
        online = sum(s["state"] == "ONLINE" and s["cluster_health"]["ok"] for s in statuses)
        failed = sum(s["state"] == "FAILED" or not s["cluster_health"]["ok"] for s in statuses)
        return {"ok": bool(statuses) and online > 0,
                "mode": "SIMULATED_BRAIN_BLADE_SERVER_FABRIC",
                "fabric_id": self.fabric_id, "blade_count": len(statuses),
                "online_blades": online, "failed_blades": failed,
                "blades": statuses, "task_slots_per_blade": self.task_slots_per_blade,
                "cloud_resources_provisioned": False, "network_listener_enabled": False,
                "physical_hardware": False}

    def checkpoint(self) -> dict:
        return {"schema": "brain-blade-fabric-checkpoint-v1",
                "mode": "SIMULATED_BRAIN_BLADE_SERVER_FABRIC",
                "fabric_id": self.fabric_id, "ram_cells_per_task": self.ram_cells_per_task,
                "clock_width_bits": self.clock_width_bits,
                "task_slots_per_blade": self.task_slots_per_blade, "cursor": self._cursor,
                "blades": [{"blade_id": bid, "state": b["state"],
                            "cluster": b["cluster"].checkpoint()} for bid, b in self.blades.items()],
                "events": [dict(e) for e in self.events], "physical_hardware": False}

    def restore_checkpoint(self, checkpoint: dict) -> dict:
        if not isinstance(checkpoint, dict) or checkpoint.get("schema") != "brain-blade-fabric-checkpoint-v1":
            raise ValueError("FABRIC_CHECKPOINT_SCHEMA_UNSUPPORTED")
        if checkpoint.get("mode") != "SIMULATED_BRAIN_BLADE_SERVER_FABRIC":
            raise ValueError("FABRIC_CHECKPOINT_MODE_INVALID")
        try:
            fid, ram, width, slots, cursor = (checkpoint[k] for k in
                ("fabric_id", "ram_cells_per_task", "clock_width_bits", "task_slots_per_blade", "cursor"))
            raw_blades, raw_events = checkpoint["blades"], checkpoint["events"]
        except (KeyError, TypeError) as exc:
            raise ValueError("FABRIC_CHECKPOINT_MALFORMED") from exc
        if not isinstance(fid, str) or not fid.strip():
            raise ValueError("FABRIC_CHECKPOINT_ID_INVALID")
        for value, label, minimum in ((ram, "RAM", 1), (width, "CLOCK", 1),
                                      (slots, "TASK_SLOTS", 1), (cursor, "CURSOR", 0)):
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                raise ValueError(f"FABRIC_CHECKPOINT_{label}_INVALID")
        if not isinstance(raw_blades, list) or not isinstance(raw_events, list):
            raise ValueError("FABRIC_CHECKPOINT_COLLECTION_INVALID")
        candidate_blades = {}
        for item in raw_blades:
            if not isinstance(item, dict):
                raise ValueError("FABRIC_CHECKPOINT_BLADE_INVALID")
            bid, state = item.get("blade_id"), item.get("state")
            if not isinstance(bid, str) or not bid.strip() or bid in candidate_blades:
                raise ValueError("FABRIC_CHECKPOINT_BLADE_ID_INVALID")
            if state not in self.VALID_STATES:
                raise ValueError("FABRIC_CHECKPOINT_BLADE_STATE_INVALID")
            cluster = BrainVirtualClusterManager(ram_cells_per_task=ram, clock_width_bits=width)
            cluster.restore_checkpoint(item.get("cluster"))
            if cluster.cluster_id != f"{fid.strip()}:{bid}":
                raise ValueError("FABRIC_CHECKPOINT_CLUSTER_ID_MISMATCH")
            candidate_blades[bid] = {"state": state, "cluster": cluster}
        events = []
        for event in raw_events:
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise ValueError("FABRIC_CHECKPOINT_EVENT_INVALID")
            events.append(dict(event))
        self.fabric_id, self.ram_cells_per_task = fid.strip(), ram
        self.clock_width_bits, self.task_slots_per_blade = width, slots
        self._cursor, self.blades, self.events = cursor, candidate_blades, events
        return self.health()

    def _get_blade(self, blade_id: str) -> dict:
        if blade_id not in self.blades:
            raise KeyError("FABRIC_BLADE_NOT_FOUND")
        return self.blades[blade_id]

    def _event(self, event_type: str, **details) -> None:
        self.events.append({"type": event_type, **details})
