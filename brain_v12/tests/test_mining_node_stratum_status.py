"""Read-only Stratum pipeline status contract tests."""
from brain_v12.brain.mining_node_api import (
    get_stratum_candidate_pipeline_status,
    router,
    stratum_candidate_pipeline_status,
)


def test_stratum_pipeline_status_is_capability_only():
    result = stratum_candidate_pipeline_status()
    assert result["ok"] is True
    assert result["status"] == "AVAILABLE_OFFLINE_BOUNDED"
    assert result["prepare_and_search_job_available"] is True
    assert result["network_target_validation_available"] is True
    assert result["execution_performed"] is False
    assert result["network_access_performed"] is False
    assert result["pool_contacted"] is False
    assert result["share_submitted"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False


def test_stratum_pipeline_status_route_is_read_only():
    route = next(route for route in router.routes if getattr(route, "path", None) == "/api/mining-node/stratum-pipeline/status")
    assert route.methods == {"GET"}
    result = get_stratum_candidate_pipeline_status()
    assert result["execution_performed"] is False
    assert result["pool_contacted"] is False
