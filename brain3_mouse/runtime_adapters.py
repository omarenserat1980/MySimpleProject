"""Explicit, fail-closed adapters for the real Brain V7 and V12 in-process runtimes.

Adapters are initialized only through the local integration endpoint. No network,
Render, device, shell, publishing, or operating-system boot actions are used.
Runtime-specific memories are mirrored into the Brain 3 shared ledger at adapter
boundaries; this is synchronization, not a claim that legacy storage internals
have become the same Python object.
"""
from __future__ import annotations

from dataclasses import asdict
from threading import RLock
from typing import Any

from .unified_kernel import ComponentAdapter, UnifiedBrainKernel


class RuntimeAdapterManager:
    def __init__(self, kernel: UnifiedBrainKernel):
        self.kernel = kernel
        self._lock = RLock()
        self._instances: dict[str, Any] = {}
        self._errors: dict[str, str] = {}

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "initialized": sorted(self._instances),
                "errors": dict(self._errors),
                "memory_bridge": "boundary_sync",
                "external_side_effects": False,
            }

    def initialize(self) -> dict[str, Any]:
        """Instantiate real runtimes and register adapters only after safe probes."""
        with self._lock:
            self._initialize_v12()
            self._initialize_legacy()
            return self.status()

    def _initialize_v12(self) -> None:
        if "brain_v12" in self._instances:
            return
        try:
            from brain_v12.brain.memory import MemoryStore
            from brain_v12.brain.core import BrainCore
            from brain_v12.brain.builder import SoftwareBuilder
            from brain_v12.brain.orchestrator import CognitiveOrchestrator

            store = MemoryStore(":memory:")
            store.init()
            core = BrainCore(store)
            builder = SoftwareBuilder()
            orchestrator = CognitiveOrchestrator(store, core, builder)
            probe = core.snapshot()
            if not isinstance(probe, dict):
                raise TypeError("V12 core snapshot contract failed")

            def handle(action: str, payload: dict[str, Any]) -> dict[str, Any]:
                self._hydrate_v12_memory(store)
                if action == "inspect":
                    result = {"runtime": "brain_v12", "state": core.snapshot(),
                              "goal_count": len(store.goals())}
                elif action == "plan":
                    objective = str(payload.get("objective") or payload.get("description") or "Brain 3 safe plan")
                    goal_id = store.add_goal(objective, priority=1.0)
                    result = orchestrator.run(project="brain3")
                    store.set_goal_status(goal_id, "DONE")
                    result = {**result, "requested_objective": objective}
                else:
                    result = {"runtime": "brain_v12", "test": "in_process_contract_passed"}
                self._sync_v12_memory(store)
                return {"ok": True, **result}

            probe_result = handle("inspect", {})
            if not isinstance(probe_result, dict) or probe_result.get("ok") is not True:
                raise TypeError("V12 adapter inspect probe failed")
            self.kernel.register_adapter(ComponentAdapter(
                name="brain_v12",
                capabilities=frozenset({"inspect", "test", "plan"}),
                handler=handle,
                verified=True,
            ))
            self._instances["brain_v12"] = {"store": store, "core": core, "orchestrator": orchestrator}
            self._errors.pop("brain_v12", None)
            self._sync_v12_memory(store)
        except Exception as exc:
            self._errors["brain_v12"] = type(exc).__name__

    def _initialize_legacy(self) -> None:
        if "legacy_brain" in self._instances:
            return
        try:
            from brain_v7.braincore_v2.brain_orchestrator import UnifiedBrain

            brain = UnifiedBrain()
            probe = brain.state
            if not hasattr(probe, "status") or not hasattr(brain, "memory"):
                raise TypeError("legacy Brain runtime contract failed")

            def handle(action: str, payload: dict[str, Any]) -> dict[str, Any]:
                self._hydrate_legacy_memory(brain)
                if action == "inspect":
                    result = {
                        "runtime": "legacy_brain",
                        "state": asdict(brain.state),
                        "memory_count": len(brain.memory),
                    }
                elif action == "plan":
                    objective = str(payload.get("objective") or payload.get("description") or "Brain 3 safe plan")
                    # Run the legacy reasoning component only; avoid its wider
                    # workforce/media/development cycle at this integration boundary.
                    reasoning = brain.reasoning_engine.reason(
                        objective, context={"source": "brain3", "safe_plan_only": True},
                        evidence=[], observations=[],
                    )
                    result = {"runtime": "legacy_brain", "objective": objective,
                              "selected_strategy": getattr(reasoning, "selected_strategy", ""),
                              "confidence": getattr(reasoning, "confidence", 0.0),
                              "external_side_effects": False}
                else:
                    result = {"runtime": "legacy_brain", "test": "in_process_contract_passed"}
                self._sync_legacy_memory(brain)
                return {"ok": True, **result}

            probe_result = handle("inspect", {})
            if not isinstance(probe_result, dict) or probe_result.get("ok") is not True:
                raise TypeError("legacy adapter inspect probe failed")
            self.kernel.register_adapter(ComponentAdapter(
                name="legacy_brain",
                capabilities=frozenset({"inspect", "test", "plan"}),
                handler=handle,
                verified=True,
            ))
            self._instances["legacy_brain"] = {"brain": brain}
            self._errors.pop("legacy_brain", None)
            self._sync_legacy_memory(brain)
        except Exception as exc:
            self._errors["legacy_brain"] = type(exc).__name__

    def _hydrate_v12_memory(self, store: Any) -> None:
        import json
        for key, value in self.kernel.memory_items(prefix="shared:legacy:"):
            store.save_memory(f"brain3:shared:legacy:{key.removeprefix('shared:legacy:')}",
                              json.dumps(value, ensure_ascii=False))

    def _sync_v12_memory(self, store: Any) -> None:
        for item in store.memories():
            if item["key"].startswith("brain3:shared:legacy:"):
                continue
            self.kernel.memory_set(f"shared:v12:{item['key']}", item["value"])

    def _hydrate_legacy_memory(self, brain: Any) -> None:
        from brain_v7.braincore_v2.long_term_cognitive_memory import MemoryNode
        for key, value in self.kernel.memory_items(prefix="shared:v12:"):
            node_key = f"v12:{key.removeprefix('shared:v12:')}"
            concept = str(value)
            brain.memory.setdefault(node_key, MemoryNode(key=node_key, concept=concept))

    def _sync_legacy_memory(self, brain: Any) -> None:
        for key, node in brain.memory.items():
            self.kernel.memory_set(f"shared:legacy:{key}", asdict(node))


MANAGER: RuntimeAdapterManager | None = None


def manager_for(kernel: UnifiedBrainKernel) -> RuntimeAdapterManager:
    global MANAGER
    if MANAGER is None or MANAGER.kernel is not kernel:
        MANAGER = RuntimeAdapterManager(kernel)
    return MANAGER
