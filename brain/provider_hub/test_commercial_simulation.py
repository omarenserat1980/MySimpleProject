from brain.provider_hub.commercial_simulation import run_safe_simulation


def test_end_to_end_commercial_gates():
    result = run_safe_simulation()
    assert result["final_state"] == "DELIVERY_VERIFIED"
