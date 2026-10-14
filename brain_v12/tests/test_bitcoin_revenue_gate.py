from brain_v12.brain.bitcoin_revenue_gate import RevenueEvidence, evaluate


def test_final_gate_blocks_without_real_evidence():
    result = evaluate(RevenueEvidence(False, False, 0, False))
    assert result["status"] == "BLOCKED"
    assert result["revenue_realized"] is False


def test_final_gate_accepts_complete_real_evidence():
    result = evaluate(
        RevenueEvidence(
            worker_authorized=True,
            pool_connected=True,
            accepted_shares=1,
            payout_observed=True,
            payout_txid="real-tx",
            btc_received=0.000001,
        )
    )
    assert result["status"] == "REVENUE_REALIZED"
    assert result["revenue_realized"] is True
