from brain_v12.brain.worker_registry import WorkerRegistry


class FakeDeviceBridge:
    def __init__(self, agents=None, fail=False):
        self.agents = agents or []
        self.fail = fail

    def agent_status(self):
        if self.fail:
            raise RuntimeError("optional adapter unavailable")
        return {"agents": self.agents}


def test_register_and_lease():
    registry = WorkerRegistry(ttl_seconds=15)
    snapshot = registry.register("software-01", "software", {"python"}, lease_seconds=30, now=100.0)
    assert snapshot["targets"][0]["online"]
    assert snapshot["targets"][0]["worker_id"] == "software-01"
    assert snapshot["mode"] == "software-first"


def test_expired_worker_is_offline():
    registry = WorkerRegistry(ttl_seconds=15)
    registry.register("software-01", "software", {"python"}, lease_seconds=10, now=100.0)
    assert not registry.targets(now=111.0)[0].online


def test_physical_device_adapter_is_disabled_by_default():
    bridge = FakeDeviceBridge([{"agent_id": "redmi3-01", "online": True}])
    registry = WorkerRegistry(bridge)
    assert all(target.kind != "device" for target in registry.targets(now=100))
    assert registry.snapshot(now=100)["device_adapters_enabled"] is False


def test_device_adapter_requires_explicit_opt_in():
    bridge = FakeDeviceBridge([{"agent_id": "redmi3-01", "online": True}])
    registry = WorkerRegistry(bridge, include_device_adapters=True)
    assert any(target.worker_id == "redmi3-01" for target in registry.targets(now=100))


def test_optional_device_adapter_failure_does_not_break_software_workers():
    registry = WorkerRegistry(FakeDeviceBridge(fail=True))
    registry.register("software-01", "software", {"python"}, now=100)
    assert [target.worker_id for target in registry.targets(now=100)] == ["software-01"]


def test_worker_id_must_be_present():
    import pytest
    with pytest.raises(ValueError, match="WORKER_ID_REQUIRED"):
        WorkerRegistry().register(" ", "software", {"python"}, now=100)
