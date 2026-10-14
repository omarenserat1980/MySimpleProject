import pytest
from unittest.mock import patch

from brain_v12.business.bitcoin_chain_readonly_collector import collect_bitcoin_chain_transaction

TXID = "a" * 64


def transaction(**overrides):
    value = {
        "txid": TXID,
        "status": {"confirmed": True, "block_height": 100},
        "vout": [
            {"scriptpubkey_address": "bc1qwallet", "value": 125000},
            {"scriptpubkey_address": "bc1qother", "value": 2000},
        ],
    }
    return value | overrides


def test_collects_confirmed_chain_evidence_read_only():
    with patch(
        "brain_v12.business.bitcoin_chain_readonly_collector._get_json",
        side_effect=[transaction(), 105],
    ):
        result = collect_bitcoin_chain_transaction(TXID)
    assert result["status"] == "CONFIRMED"
    assert result["confirmations"] == 6
    assert result["outputs"][0] == {"address": "bc1qwallet", "value_sats": 125000}
    assert result["source_url"] == f"https://mempool.space/tx/{TXID}"
    assert result["evidence_origin"] == "LIVE_PUBLIC_EXPLORER_API"
    assert result["pool_payout_verified"] is False
    assert result["revenue_realized"] is False
    assert result["external_actions_enabled"] is False


def test_unconfirmed_transaction_does_not_fetch_tip_height():
    with patch(
        "brain_v12.business.bitcoin_chain_readonly_collector._get_json",
        return_value=transaction(status={"confirmed": False}),
    ) as fetch:
        result = collect_bitcoin_chain_transaction(TXID)
    assert result["status"] == "UNCONFIRMED"
    assert result["confirmations"] == 0
    assert fetch.call_count == 1


def test_rejects_invalid_txid_before_network_call():
    with patch("brain_v12.business.bitcoin_chain_readonly_collector._get_json") as fetch:
        with pytest.raises(ValueError, match="64-character hexadecimal"):
            collect_bitcoin_chain_transaction("not-a-txid")
    fetch.assert_not_called()


def test_rejects_mismatched_explorer_response():
    with patch(
        "brain_v12.business.bitcoin_chain_readonly_collector._get_json",
        return_value=transaction(txid="b" * 64),
    ):
        with pytest.raises(ValueError, match="does not match"):
            collect_bitcoin_chain_transaction(TXID)


def test_rejects_invalid_tip_height_and_output_values():
    with patch(
        "brain_v12.business.bitcoin_chain_readonly_collector._get_json",
        side_effect=[transaction(), 99],
    ):
        with pytest.raises(ValueError, match="tip height"):
            collect_bitcoin_chain_transaction(TXID)
    with patch(
        "brain_v12.business.bitcoin_chain_readonly_collector._get_json",
        return_value=transaction(status={"confirmed": False}, vout=[{"scriptpubkey_address": "bc1qwallet", "value": -1}]),
    ):
        with pytest.raises(ValueError, match="non-negative integer"):
            collect_bitcoin_chain_transaction(TXID)
