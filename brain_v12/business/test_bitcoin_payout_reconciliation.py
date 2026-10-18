import pytest

from brain_v12.business.bitcoin_payout_reconciliation import audit_realized_bitcoin_payout


TXID = "a" * 64


def pool(**overrides):
    data = {
        "provider": "ExamplePool",
        "payout_id": "payout-123",
        "network": "bitcoin",
        "txid": TXID,
        "destination": "bc1qrealwallet",
        "received_sats": 125000,
        "status": "confirmed",
        "source_url": "https://pool.example/account/payouts/payout-123",
    }
    return data | overrides


def chain(**overrides):
    data = {
        "network": "bitcoin",
        "txid": TXID,
        "confirmations": 6,
        "status": "CONFIRMED",
        "outputs": [
            {"address": "bc1qrealwallet", "value_sats": 125000},
            {"address": "bc1qother", "value_sats": 9000},
        ],
        "source_url": f"https://mempool.space/tx/{TXID}",
        "observed_at": "2026-10-14T10:00:00Z",
    }
    return data | overrides


def test_reconciles_pool_payout_with_independent_chain_output():
    result = audit_realized_bitcoin_payout(pool_payout=pool(), chain_transaction=chain())
    assert result["status"] == "MATCHED_ONCHAIN_OUTPUT_REQUIRES_TRUSTED_POOL_VERIFICATION"
    assert result["revenue_realized"] is False
    assert result["pool_source_independently_verified"] is False
    assert result["onchain_output_amount_matched"] is True
    assert result["received_sats"] == 125000
    assert result["received_btc"] == "0.00125000"
    assert result["proof_policy"]["network_calls_performed"] is False
    assert result["proof_policy"]["evidence_freshness_verified"] is True
    assert result["proof_policy"]["pool_source_independently_verified"] is False


@pytest.mark.parametrize(
    ("payout", "transaction", "message"),
    [
        (pool(txid="tx-123"), chain(), "64-character hexadecimal"),
        (pool(), chain(txid="b" * 64), "does not match"),
        (pool(), chain(confirmations=2), "insufficient blockchain confirmations"),
        (pool(), chain(status="PENDING"), "must be CONFIRMED"),
        (pool(), chain(source_url="https://untrusted.example/tx/" + TXID), "recognized public"),
        (pool(), chain(outputs=[{"address": "bc1qrealwallet", "value_sats": 124999}]), "does not match"),
        (pool(), chain(network="testnet"), "bitcoin network"),
        (pool(status="pending"), chain(), "completed/confirmed"),
    ],
)
def test_rejects_unproven_or_mismatched_payout(payout, transaction, message):
    with pytest.raises(ValueError, match=message):
        audit_realized_bitcoin_payout(pool_payout=payout, chain_transaction=transaction)


def test_rejects_missing_pool_identity_and_non_https_sources():
    with pytest.raises(ValueError, match="provider, payout_id, and destination"):
        audit_realized_bitcoin_payout(
            pool_payout=pool(provider=""),
            chain_transaction=chain(),
        )
    with pytest.raises(ValueError, match="HTTPS"):
        audit_realized_bitcoin_payout(
            pool_payout=pool(),
            chain_transaction=chain(source_url="http://mempool.space/tx/" + TXID),
        )


def test_rejects_same_source_url_for_pool_and_chain_evidence():
    url = f"https://mempool.space/tx/{TXID}"
    with pytest.raises(ValueError, match="distinct source URLs"):
        audit_realized_bitcoin_payout(
            pool_payout=pool(source_url=url),
            chain_transaction=chain(source_url=url),
        )


@pytest.mark.parametrize(
    ("timestamp", "message"),
    [
        ("not-a-timestamp", "valid ISO 8601"),
        ("2026-10-14T10:00:00", "must include a timezone"),
        ("2020-01-01T00:00:00Z", "evidence is stale"),
        ("2099-01-01T00:00:00Z", "timestamp is in the future"),
    ],
)
def test_rejects_invalid_stale_or_future_chain_evidence_timestamps(timestamp, message):
    with pytest.raises(ValueError, match=message):
        audit_realized_bitcoin_payout(
            pool_payout=pool(),
            chain_transaction=chain(observed_at=timestamp),
        )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"minimum_confirmations": True}, "minimum_confirmations must be an integer"),
        ({"minimum_confirmations": 0}, "minimum_confirmations must be an integer"),
        ({"max_evidence_age_seconds": True}, "max_evidence_age_seconds must be an integer"),
        ({"max_evidence_age_seconds": 0}, "max_evidence_age_seconds must be an integer"),
    ],
)
def test_rejects_invalid_freshness_and_confirmation_policy(kwargs, message):
    with pytest.raises(ValueError, match=message):
        audit_realized_bitcoin_payout(
            pool_payout=pool(),
            chain_transaction=chain(),
            **kwargs,
        )
