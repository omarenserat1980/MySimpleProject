from datetime import datetime, timedelta, timezone

import pytest

from brain_v12.brain.golden_mission_evidence_assembler import assemble


def _probe():
    return {
        "status": "PARTIAL",
        "source": "live_read_only_runtime_probe",
        "target_host": "brain.internal",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": [
            {"name": "runtime_api_readiness", "passed": True, "response_sha256": "a" * 64},
            {"name": "runtime_worker_status", "passed": True, "response_sha256": "b" * 64},
        ],
        "safety": {
            "executes_missions": False,
            "changes_service_state": False,
            "stores_control_key": False,
        },
    }


def _drill(name):
    return {
        "source": name,
        "target_host": "brain.internal",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": [{
            "name": name,
            "passed": True,
            "evidence_ref": f"artifact://{name}/log.txt",
            "evidence_sha256": "c" * 64,
        }],
    }


def test_assembler_requires_both_real_drill_records():
    report = assemble(_probe(), _drill("mission_persistence_restart"), _drill("restore_drill"))
    assert report["status"] == "VERIFIED"
    assert {item["name"] for item in report["checks"]} == {
        "runtime_api_readiness", "runtime_worker_status",
        "mission_persistence_restart", "restore_drill",
    }
    assert report["safety"]["restart_and_restore_are_operator_supplied_evidence"] is True


@pytest.mark.parametrize("field,value", [
    ("source", "manual"),
    ("target_host", "another-host"),
    ("checked_at", (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()),
])
def test_assembler_rejects_untrusted_mismatched_or_stale_drill(field, value):
    restart = _drill("mission_persistence_restart")
    restart[field] = value
    with pytest.raises(ValueError):
        assemble(_probe(), restart, _drill("restore_drill"))


def test_assembler_rejects_missing_or_invalid_evidence_hash():
    restore = _drill("restore_drill")
    restore["checks"][0]["evidence_sha256"] = "not-a-hash"
    with pytest.raises(ValueError):
        assemble(_probe(), _drill("mission_persistence_restart"), restore)


def test_assembler_cannot_upgrade_blocked_live_probe():
    probe = _probe()
    probe["status"] = "BLOCKED"
    with pytest.raises(ValueError):
        assemble(probe, _drill("mission_persistence_restart"), _drill("restore_drill"))
