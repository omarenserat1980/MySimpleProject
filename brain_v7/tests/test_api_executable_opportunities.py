from brain_v7.braincore_v2.api_executable_opportunities import (
    catalog,
    execution_gate,
    executable_routes,
)


def test_catalog_contains_api_routes():
    assert len(catalog()) >= 5


def test_disconnected_provider_has_no_executable_routes():
    assert executable_routes(
        provider_connected=False,
        authenticated=False,
        api_scope_authorized=False,
    ) == []


def test_gate_requires_explicit_authorization():
    result = execution_gate(
        artifact_ready=True,
        provider_connected=True,
        authenticated=True,
        api_scope_authorized=True,
        explicit_job_authorization=False,
    )
    assert result["status"] == "BLOCKED"
    assert "EXPLICIT_JOB_AUTHORIZATION_REQUIRED" in result["blockers"]


def test_ready_gate_still_does_not_claim_payment():
    result = execution_gate(
        artifact_ready=True,
        provider_connected=True,
        authenticated=True,
        api_scope_authorized=True,
        explicit_job_authorization=True,
    )
    assert result["status"] == "READY_FOR_API_EXECUTION"
    assert result["payment_verified"] is False
