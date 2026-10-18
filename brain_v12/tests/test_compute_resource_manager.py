import json

import pytest

from brain_v12.brain.compute_resource_manager import (
    MAX_BOUNDED_HASHES,
    MAX_BOUNDED_SECONDS,
    build_compute_resource_report,
)


def test_report_is_read_only_and_fails_closed_for_live_mining():
    report = build_compute_resource_report()
    assert report["evidence_class"] == "READ_ONLY_LOCAL_RESOURCE_INVENTORY"
    assert report["resources"]["cpu_logical_count"] is None or report["resources"]["cpu_logical_count"] > 0
    assert report["execution_gates"]["live_mining_authorized"] is False
    assert report["execution_gates"]["share_submission_enabled"] is False
    assert report["execution_gates"]["pool_acceptance_verified"] is False
    assert report["execution_gates"]["revenue_verified"] is False
    assert report["safety"] == {
        "network_access_performed": False,
        "subprocesses_started": False,
        "secret_values_read": False,
        "files_modified": False,
        "mining_started": False,
    }


def test_compute_budgets_are_clamped_to_hard_ceilings():
    report = build_compute_resource_report(
        requested_hashes=MAX_BOUNDED_HASHES + 1,
        requested_seconds=MAX_BOUNDED_SECONDS + 10,
    )
    plan = report["bounded_compute_plan"]
    assert plan["hash_budget"] == MAX_BOUNDED_HASHES
    assert plan["time_budget_seconds"] == MAX_BOUNDED_SECONDS
    assert plan["hash_budget_capped"] is True
    assert plan["time_budget_capped"] is True


@pytest.mark.parametrize("kwargs", [
    {"requested_hashes": 0},
    {"requested_hashes": -1},
    {"requested_hashes": True},
    {"requested_hashes": 1.5},
    {"requested_seconds": 0},
    {"requested_seconds": -1},
    {"requested_seconds": float("nan")},
])
def test_invalid_budgets_rejected(kwargs):
    with pytest.raises(ValueError):
        build_compute_resource_report(**kwargs)


def test_termux_is_detected_without_device_or_network_probe(monkeypatch):
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    monkeypatch.delenv("TERMUX_VERSION", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    report = build_compute_resource_report()
    assert report["runtime"]["kind"] == "ANDROID_TERMUX"
    assert report["safety"]["network_access_performed"] is False
    assert report["execution_gates"]["live_mining_authorized"] is False


def test_report_is_json_serializable():
    assert json.loads(json.dumps(build_compute_resource_report()))["schema"] == (
        "brain-compute-resource-report/v1"
    )
