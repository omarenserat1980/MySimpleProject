from brain_v12.brain.worker_registry import WorkerRegistry

def test_register_and_lease():
    r=WorkerRegistry(ttl_seconds=15)
    s=r.register("cloud-01","cloud",{"python"},lease_seconds=30,now=100.0)
    assert s["targets"][0]["online"]
    assert s["targets"][0]["worker_id"]=="cloud-01"

def test_expired_worker_is_offline():
    r=WorkerRegistry(ttl_seconds=15)
    r.register("cloud-01","cloud",{"python"},lease_seconds=10,now=100.0)
    assert not r.targets(now=111.0)[0].online

def test_device_heartbeat_source_is_used():
    class B:
        def agent_status(self):
            return {"agents":[{"agent_id":"redmi3-01","online":True}]}
    r=WorkerRegistry(B())
    ids={x.worker_id for x in r.targets(now=100)}
    assert "redmi3-01" in ids
