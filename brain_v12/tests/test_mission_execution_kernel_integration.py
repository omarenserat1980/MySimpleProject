from brain_v12.brain.execution_kernel import ExecutionKernel
from brain_v12.brain.resource_fabric import ResourceFabric, ResourceKind, ResourceRequest, ResourceSpec
from brain_v12.integration.execution_coordinator import MissionExecutionCoordinator


def make_fabric():
    f = ResourceFabric(lease_seconds=60)
    f.register(ResourceSpec("cpu", ResourceKind.COMPUTE, "host", 8, "core", {"blade_id": "blade-1"}))
    f.register(ResourceSpec("ram", ResourceKind.MEMORY, "host", 16, "gb", {"blade_id": "blade-1"}))
    return f


def reqs(cpu=2, ram=4):
    return [
        ResourceRequest(ResourceKind.COMPUTE, cpu, "core", co_locate_key="m"),
        ResourceRequest(ResourceKind.MEMORY, ram, "gb", co_locate_key="m"),
    ]


def test_admission_binds_mission_kernel_and_resources(tmp_path):
    k = ExecutionKernel(tmp_path / "kernel.json", lease_seconds=60)
    c = MissionExecutionCoordinator(make_fabric(), k)
    r = c.admit(mission="analyze the project", owner="brain", requests=reqs(), evidence_confidence=0.9)
    assert r["ok"] is True
    assert r["status"] == "ADMITTED"
    assert r["execution"]["epoch"] == 1
    assert r["reservation"]["status"] == "RESERVED"
    done = c.finish(r["execution"]["execution_id"], r["execution"]["epoch"], r["reservation"]["reservation_id"])
    assert done["ok"] is True


def test_capacity_blocks_before_kernel(tmp_path):
    k = ExecutionKernel(tmp_path / "kernel.json")
    c = MissionExecutionCoordinator(make_fabric(), k)
    r = c.admit(mission="analyze the project", owner="brain",
                requests=reqs(cpu=99), evidence_confidence=0.9)
    assert r["status"] == "CAPACITY_BLOCKED"
    assert k.status()["active"] is None


def test_external_side_effect_requires_authorization(tmp_path):
    k = ExecutionKernel(tmp_path / "kernel.json")
    c = MissionExecutionCoordinator(make_fabric(), k)
    r = c.admit(mission="send an external payment", owner="brain",
                requests=reqs(), evidence_confidence=0.9, external_side_effects=True)
    assert r["status"] == "AUTHORIZATION_REQUIRED"
    assert k.status()["active"] is None
