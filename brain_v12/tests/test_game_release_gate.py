from brain_v12.business.game_release_gate import evaluate

def test_game_release_gate_requires_independent_evidence():
    assert not evaluate(built=True,tests_passed=True,artifact_present=True,evidence_ref=None).ready
    assert evaluate(built=True,tests_passed=True,artifact_present=True,evidence_ref="ev-1").ready
