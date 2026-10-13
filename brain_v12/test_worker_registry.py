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
    assert snapshot["mode"] == "software-only"


def test_expired_worker_is_offline():
    registry = WorkerRegistry(ttl_seconds=15)
    registry.register("software-01", "software", {"python"}, lease_seconds=10, now=100.0)
    assert not registry.targets(now=111.0)[0].online


def test_public_snapshot_hides_last_seen_but_heartbeat_and_lease_still_work():
    registry = WorkerRegistry(ttl_seconds=15)
    registry.register("software-01", "software", {"python"}, lease_seconds=10, now=100.0)

    snapshot = registry.snapshot(now=101.0)
    assert "last_seen" not in snapshot["workers"][0]
    assert registry.targets(now=109.0)[0].online

    registry.heartbeat("software-01", now=110.0)
    assert registry.targets(now=139.0)[0].online
    assert not registry.targets(now=141.0)[0].online


def test_physical_device_adapters_are_disabled_even_if_requested():
    bridge = FakeDeviceBridge([{"agent_id": "redmi3-01", "online": True}])
    registry = WorkerRegistry(bridge, include_device_adapters=True)
    snapshot = registry.snapshot(now=100)
    assert registry.targets(now=100) == []
    assert snapshot["device_adapters_enabled"] is False
    assert snapshot["device_workers"] == []


def test_physical_worker_registration_is_rejected():
    import pytest
    for kind in ("device", "physical", "termux", "android", "hardware"):
        with pytest.raises(ValueError, match="PHYSICAL_DEVICE_WORKERS_DISABLED"):
            WorkerRegistry().register("legacy-device", kind, now=100)


def test_legacy_device_bridge_is_never_called():
    registry = WorkerRegistry(FakeDeviceBridge(fail=True))
    registry.register("software-01", "software", {"python"}, now=100)
    assert [target.worker_id for target in registry.targets(now=100)] == ["software-01"]


def test_worker_id_must_be_present():
    import pytest
    with pytest.raises(ValueError, match="WORKER_ID_REQUIRED"):
        WorkerRegistry().register(" ", "software", { "python" }, now=100)
