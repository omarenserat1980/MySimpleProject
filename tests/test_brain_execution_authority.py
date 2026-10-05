from datetime import datetime, timezone, timedelta
import json

from platform_foundation.brain_execution_authority import BrainExecutionAuthority


def test_brain_executor_heartbeat_proves_readiness(tmp_path):
    authority = BrainExecutionAuthority(
        executor_id="brain-local-test",
        heartbeat_path=tmp_path / "heartbeat.json",
    )
    authority.heartbeat()
    result = authority.readiness()
    assert result["ready"] is True
    assert result["executor"]["owner"] == "brain"
    assert result["executor"]["persistent"] is True


def test_missing_or_stale_heartbeat_blocks(tmp_path):
    path = tmp_path / "heartbeat.json"
    authority = BrainExecutionAuthority(
        executor_id="brain-local-test",
        heartbeat_path=path,
        max_heartbeat_age_seconds=1,
    )
    path.write_text(json.dumps({
        "executor_id": "brain-local-test",
        "owner": "brain",
        "persistent": True,
        "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat(),
        "capabilities": ["ci"],
    }))
    assert authority.readiness()["ready"] is False
