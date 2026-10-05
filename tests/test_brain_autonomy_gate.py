import json

import tools.brain_autonomy_gate as gate


def test_autonomy_gate_fails_closed(monkeypatch, capsys):
    monkeypatch.setattr(
        gate,
        "evaluate",
        lambda: {
            "status": "NOT_AUTONOMOUS",
            "reason": "live_executor:offline",
            "AUTONOMOUS_WITHIN_AUTHORITY": False,
        },
    )
    assert gate.main() == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "NOT_AUTONOMOUS"


def test_autonomy_gate_passes_only_when_live(monkeypatch, capsys):
    monkeypatch.setattr(
        gate,
        "evaluate",
        lambda: {
            "status": "AUTONOMOUS_WITHIN_AUTHORITY",
            "reason": "scoped_proof_and_live_brain_executor_ready",
            "AUTONOMOUS_WITHIN_AUTHORITY": True,
        },
    )
    assert gate.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["AUTONOMOUS_WITHIN_AUTHORITY"] is True
