from pathlib import Path

from platform_foundation.brain_execution_authority import BrainExecutionAuthority


def test_worker_authority_contract_is_brain_owned(tmp_path):
    authority = BrainExecutionAuthority(
        executor_id="brain-local-test",
        heartbeat_path=tmp_path / "heartbeat.json",
    )
    payload = authority.heartbeat()
    assert payload["owner"] == "brain"
    assert payload["persistent"] is True
    assert authority.readiness("ci")["ready"] is True
