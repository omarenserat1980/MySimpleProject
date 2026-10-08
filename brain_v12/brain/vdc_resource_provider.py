from __future__ import annotations

"""Transactional bridge between Resource Fabric and BrainVirtualDatacenter."""

from dataclasses import dataclass

from .resource_fabric import ResourceFabric, ResourceKind, ResourceRequest
from .resource_manager import ResourceRequirement


@dataclass
class FabricVDCBinding:
    reservation_id: str
    task_id: str
    blade_id: str


class VirtualDatacenterResourceProvider:
    """Makes Fabric composition consume the VDC's real accounting layer."""

    def __init__(self, vdc, fabric: ResourceFabric):
        self.vdc = vdc
        self.fabric = fabric
        self.bindings: dict[str, FabricVDCBinding] = {}

    @staticmethod
    def _gb(value_bytes: int) -> int:
        return max(0, int(value_bytes) // (1024 ** 3))

    def compose_server(
        self,
        intent_id: str,
        cpu_cores: int = 1,
        ram_bytes: int = 4 * 1024 * 1024 * 1024,
        storage_bytes: int = 64 * 1024 * 1024 * 1024,
        network: bool = False,
        gpu: bool = False,
        ttl_seconds: int | None = None,
    ) -> dict:
        if cpu_cores <= 0 or ram_bytes < 0 or storage_bytes < 0:
            return {"ok": False, "status": "INVALID_REQUIREMENT"}

        # One placement group forces all VM components onto one blade.
        requests = [
            ResourceRequest(
                ResourceKind.COMPUTE, cpu_cores, "core",
                co_locate_key=intent_id,
            ),
            ResourceRequest(
                ResourceKind.MEMORY, self._gb(ram_bytes), "GB",
                co_locate_key=intent_id,
            ),
            ResourceRequest(
                ResourceKind.STORAGE, self._gb(storage_bytes), "GB",
                co_locate_key=intent_id,
            ),
        ]
        if network:
            requests.append(ResourceRequest(
                ResourceKind.NETWORK, 1, "network", co_locate_key=intent_id))
        if gpu:
            requests.append(ResourceRequest(
                ResourceKind.ACCELERATOR, 1, "gpu", co_locate_key=intent_id))

        plan = self.fabric.plan(intent_id, requests)
        if not plan["ok"]:
            return {"ok": False, "status": "PLACEMENT_BLOCKED", "plan": plan}

        blades = {
            str(self.fabric.resources[a["resource_id"]].attributes.get("blade_id"))
            for a in plan["allocations"]
        }
        blades.discard("None")
        if len(blades) != 1:
            return {"ok": False, "status": "COLOCATION_VIOLATION", "plan": plan}

        blade_id = next(iter(blades))
        blade = self.vdc.chassis.blades.get(blade_id)
        if blade is None:
            return {"ok": False, "status": "BLADE_NOT_FOUND", "blade_id": blade_id}

        requirement = ResourceRequirement(
            cpu_cores=cpu_cores,
            ram_bytes=ram_bytes,
            storage_bytes=storage_bytes,
            network=network,
            gpu=gpu,
        )
        rm = self.vdc.resource_manager.reserve(blade, intent_id, requirement)
        if not rm["ok"]:
            return {"ok": False, "status": "VDC_RESERVATION_BLOCKED",
                    "blade_id": blade_id, "resource_manager": rm, "plan": plan}

        fabric_result = self.fabric.reserve(
            intent_id,
            allocations=plan["allocations"],
            ttl_seconds=ttl_seconds,
        )
        if not fabric_result["ok"]:
            self.vdc.resource_manager.release(intent_id)
            return {"ok": False, "status": "FABRIC_RESERVATION_BLOCKED",
                    "resource_manager": rm, "fabric": fabric_result}

        reservation_id = fabric_result["reservation"]["reservation_id"]
        self.bindings[reservation_id] = FabricVDCBinding(
            reservation_id, intent_id, blade_id)
        return {
            "ok": True,
            "status": "COMPOSED",
            "intent_id": intent_id,
            "blade_id": blade_id,
            "reservation_id": reservation_id,
            "allocations": plan["allocations"],
            "resource_manager": rm,
            "fabric": fabric_result,
        }

    def release(self, reservation_id: str) -> dict:
        binding = self.bindings.get(reservation_id)
        fabric_result = self.fabric.release(reservation_id)
        if not fabric_result["ok"]:
            return fabric_result
        rm_result = self.vdc.resource_manager.release(binding.task_id) if binding else {
            "ok": False, "status": "BINDING_NOT_FOUND", "task_id": None
        }
        self.bindings.pop(reservation_id, None)
        return {
            "ok": rm_result["ok"],
            "status": "RELEASED" if rm_result["ok"] else "FABRIC_RELEASED_VDC_RELEASE_FAILED",
            "reservation_id": reservation_id,
            "fabric": fabric_result,
            "resource_manager": rm_result,
        }

    def reap_expired(self) -> dict:
        expired = self.fabric.reap_expired()
        released = []
        for reservation_id in expired:
            binding = self.bindings.pop(reservation_id, None)
            if binding:
                released.append(self.vdc.resource_manager.release(binding.task_id))
        return {"ok": True, "status": "REAP_COMPLETE",
                "expired": expired, "vdc_releases": released}
