from brain_v12.brain.resource_fabric import ResourceFabric, ResourceKind, ResourceSpec, ResourceRequest


def test_federated_capacity_aggregates_real_nodes_and_reservations():
    f = ResourceFabric()
    f.register(ResourceSpec("a-cpu", ResourceKind.COMPUTE, "node-a", 192, "core"))
    f.register(ResourceSpec("a-ram", ResourceKind.MEMORY, "node-a", 1024, "gb"))
    f.register(ResourceSpec("b-cpu", ResourceKind.COMPUTE, "node-b", 192, "core"))
    f.register(ResourceSpec("b-ram", ResourceKind.MEMORY, "node-b", 2048, "gb"))

    cap = f.federated_capacity()
    assert cap["real_capacity"]["compute:core"]["capacity"] == 384
    assert cap["real_capacity"]["memory:gb"]["capacity"] == 3072
    assert cap["real_capacity"]["compute:core"]["available"] == 384

    plan = f.plan("mission-1", [
        ResourceRequest(ResourceKind.COMPUTE, 64, "core"),
        ResourceRequest(ResourceKind.MEMORY, 512, "gb"),
    ])
    assert plan["ok"]
    reservation = f.reserve("mission-1", allocations=plan["allocations"])
    assert reservation["ok"]

    cap2 = f.federated_capacity()
    assert cap2["real_capacity"]["compute:core"]["reserved"] == 64
    assert cap2["real_capacity"]["compute:core"]["available"] == 320


def test_offline_capacity_is_not_advertised_as_available():
    f = ResourceFabric()
    f.register(ResourceSpec("cpu", ResourceKind.COMPUTE, "node-a", 192, "core",
                            state="OFFLINE"))
    cap = f.federated_capacity()
    assert cap["real_capacity"]["compute:core"]["capacity"] == 192
    assert cap["real_capacity"]["compute:core"]["available"] == 0
