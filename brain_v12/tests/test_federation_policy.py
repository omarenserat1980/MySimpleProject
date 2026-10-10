from brain_v12.brain.federation_policy import score_nodes


def test_node_scoring_penalizes_missing_capabilities():
    rows = [
        {"provider_id": "node-a", "kind": "compute", "state": "AVAILABLE"},
        {"provider_id": "node-a", "kind": "memory", "state": "AVAILABLE"},
        {"provider_id": "node-b", "kind": "compute", "state": "AVAILABLE"},
    ]
    scored = score_nodes(rows, required_kinds={"compute", "memory"})
    assert scored[0].provider_id == "node-a"
    assert scored[0].score > scored[1].score


def test_degraded_node_is_penalized():
    rows = [
        {"provider_id": "healthy", "kind": "compute", "state": "AVAILABLE"},
        {"provider_id": "degraded", "kind": "compute", "state": "DEGRADED"},
    ]
    scored = score_nodes(rows, required_kinds={"compute"})
    assert scored[0].provider_id == "healthy"
