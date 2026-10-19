"""Offline end-to-end contract test: Stratum job -> SHA256d -> submit JSON -> simulated reply.

No socket, credentials, pool connection, or real share submission is used.
A simulated positive reply remains unverified pool-reported evidence.
"""
import json

from brain_v12.brain.stratum_candidate_pipeline import prepare_and_search_job
from brain_v12.brain.stratum_share_response_evidence import observe_share_response
from brain_v12.brain.stratum_v1_jobs import StratumJob
from brain_v12.brain.stratum_v1_protocol import StratumV1Session


def _notify_params():
    return [
        "offline-integration-job", "00" * 32, "", "", [],
        "20000000", "ffff001d", "65aa0000", True,
    ]


def test_offline_job_pow_submit_and_correlated_simulated_response():
    # Protocol messages and the account-like username are local test fixtures.
    session = StratumV1Session("offline.worker", "not-a-real-secret")
    subscribe = json.loads(session.request_subscribe().decode().strip())
    session.receive(json.dumps({
        "id": subscribe["id"], "result": [[], "abcd", 2], "error": None
    }))

    authorize = json.loads(session.request_authorize().decode().strip())
    session.receive(json.dumps({
        "id": authorize["id"], "result": True, "error": None
    }))

    params = _notify_params()
    session.receive(json.dumps({"method": "mining.notify", "params": params}))
    job = StratumJob.from_notify(params)

    # Synthetic easy target: exactly one bounded SHA256d attempt, no live work.
    candidate = prepare_and_search_job(
        job,
        extranonce1_hex=session.extranonce1_hex,
        extranonce2_hex="a1b2",
        extranonce2_size=session.extranonce2_size,
        prevhash_wire_hex="00" * 32,
        share_target=(1 << 256) - 1,
        start_nonce=0,
        max_hashes=1,
    )
    assert candidate.status == "NONCE_FOUND_UNSUBMITTED"
    assert candidate.header_bytes is not None and len(candidate.header_bytes) == 80
    assert candidate.meets_share_target
    assert candidate.pool_contacted is False
    assert candidate.share_submitted is False
    assert candidate.pool_acceptance_verified is False

    nonce_hex = f"{candidate.nonce:08x}"
    submit_bytes = session.request_submit(job.job_id, "a1b2", job.ntime_hex, nonce_hex)
    submit = json.loads(submit_bytes.decode().strip())
    assert submit["method"] == "mining.submit"
    assert submit["params"] == [
        "offline.worker", job.job_id, "a1b2", job.ntime_hex, nonce_hex
    ]
    assert session.pending[submit["id"]] == "share"

    # Fabricated local fixture only; this is not a pool response or acceptance.
    evidence = observe_share_response(
        session, json.dumps({"id": submit["id"], "result": True, "error": None}),
    )
    assert evidence["pool_reported_status"] == "ACCEPTED_BY_POOL"
    assert evidence["pool_reported_acceptance"] is True
    assert evidence["live_transport_verified"] is False
    assert evidence["independent_share_validation_verified"] is False
    assert evidence["payout_verified"] is False
    assert evidence["revenue_verified"] is False
    assert evidence["financial_execution_enabled"] is False
