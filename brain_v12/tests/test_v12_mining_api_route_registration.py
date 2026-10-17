"""Catch app-import and route-registration failures in supported Python runtimes."""

from brain_v12.app import app


def test_mining_node_and_worker_routes_are_registered():
    paths = app.openapi()["paths"]
    assert "/api/mining-node/status" in paths
    assert "/api/mining-node/readiness" in paths
    assert "/api/mining-node/compute-preflight" in paths
    assert "/api/mining-node/pool-evidence/status" in paths
    assert "/api/bitcoin-mining/worker/heartbeat" in paths
    assert "/api/bitcoin-mining/worker/status" in paths
