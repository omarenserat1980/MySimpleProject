"""Pure, read-only classifier for sanitized mining-runtime diagnostic evidence.

This module does not probe networks, inspect credentials, start miners, or verify
pool claims. Callers supply observations collected by an authorized diagnostic
tool; outputs classify those observations without upgrading them into proof.
"""
from __future__ import annotations

from typing import Any

_STAGE_KEYS = ("dns", "tcp", "tls", "stratum")
_STAGE_STATES = frozenset({"PASS", "FAIL", "NOT_RUN", "UNKNOWN"})
_PROCESS_STATES = frozenset({"FOUND", "NONE_FOUND", "UNAVAILABLE", "UNKNOWN"})
_AUTH_STATES = frozenset({"ACCEPTED", "REJECTED", "NOT_TESTED", "UNKNOWN"})
_SHARE_STATES = frozenset({"ACCEPTED_REPORTED", "NONE_REPORTED", "NOT_CHECKED", "UNKNOWN"})
_ACCOUNT_STATES = frozenset({"MATCH", "MISMATCH", "NOT_CHECKED", "UNKNOWN"})


def _enum(value: Any, allowed: frozenset[str]) -> str:
    return value if isinstance(value, str) and value in allowed else "UNKNOWN"


def classify_mining_runtime_diagnosis(evidence: Any) -> dict[str, Any]:
    """Classify supplied sanitized observations, failing closed on missing data.

    Accepted values:
      process_inventory: FOUND | NONE_FOUND | UNAVAILABLE | UNKNOWN
      dns/tcp/tls/stratum: PASS | FAIL | NOT_RUN | UNKNOWN
      authorization: ACCEPTED | REJECTED | NOT_TESTED | UNKNOWN
      accepted_shares: ACCEPTED_REPORTED | NONE_REPORTED | NOT_CHECKED | UNKNOWN
      account_match: MATCH | MISMATCH | NOT_CHECKED | UNKNOWN

    A result is a diagnostic lead, not an attestation. Even ACCEPTED_REPORTED
    does not prove Brain generated the work, establish hashrate, or prove revenue.
    """
    source = evidence if isinstance(evidence, dict) else {}
    process = _enum(source.get("process_inventory"), _PROCESS_STATES)
    stages = {key: _enum(source.get(key), _STAGE_STATES) for key in _STAGE_KEYS}
    authorization = _enum(source.get("authorization"), _AUTH_STATES)
    shares = _enum(source.get("accepted_shares"), _SHARE_STATES)
    account = _enum(source.get("account_match"), _ACCOUNT_STATES)

    # Prefer a concrete failure over an absence of a local process. A remote ASIC
    # can mine without a host-side miner process, so that observation is not proof
    # that mining is absent.
    if account == "MISMATCH":
        diagnosis = "POOL_ACCOUNT_MISMATCH"
        next_action = "Verify the selected read-only API profile and account identity; do not change pool settings."
    elif stages["dns"] == "FAIL":
        diagnosis = "DNS_RESOLUTION_FAILURE"
        next_action = "Check the configured hostname and host DNS resolver using authorized read-only diagnostics."
    elif stages["tcp"] == "FAIL":
        diagnosis = "POOL_TCP_CONNECTION_FAILURE"
        next_action = "Check outbound connectivity and endpoint/port reachability without changing production configuration."
    elif stages["tls"] == "FAIL":
        diagnosis = "TLS_HANDSHAKE_FAILURE"
        next_action = "Inspect sanitized certificate/hostname/clock diagnostics; keep certificate verification enabled."
    elif stages["stratum"] == "FAIL":
        diagnosis = "STRATUM_HANDSHAKE_FAILURE"
        next_action = "Review sanitized protocol/version/response codes; do not log credentials or full authorization payloads."
    elif authorization == "REJECTED":
        diagnosis = "AUTHORIZATION_OR_WORKER_REJECTED"
        next_action = "Check the worker/account mapping with read-only evidence; do not rotate tokens or edit pool settings."
    elif all(stages[key] == "PASS" for key in _STAGE_KEYS) and shares == "NONE_REPORTED":
        diagnosis = "CONNECTED_BUT_NO_ACCEPTED_SHARES_REPORTED"
        next_action = "Inspect miner-side work/submission counters and pool-side share telemetry independently."
    elif shares == "ACCEPTED_REPORTED":
        diagnosis = "POOL_ACCEPTED_SHARES_REPORTED"
        next_action = "Independently corroborate pool-side worker/share telemetry and correlate it to an attested Brain runtime."
    elif process == "NONE_FOUND" and not any(value in {"PASS", "FAIL"} for value in stages.values()):
        diagnosis = "NO_KNOWN_HOST_MINER_PROCESS"
        next_action = "Check whether work is intended to come from an external ASIC or remote host; this inventory alone cannot decide."
    elif process == "UNAVAILABLE" and all(value in {"NOT_RUN", "UNKNOWN"} for value in stages.values()):
        diagnosis = "INSUFFICIENT_DIAGNOSTIC_CAPABILITY"
        next_action = "Run the approved read-only doctor on the actual authorized mining host and collect sanitized stage results."
    else:
        diagnosis = "INSUFFICIENT_EVIDENCE"
        next_action = "Collect only missing read-only observations from the authorized host and pool telemetry; do not infer a cause."

    return {
        "schema_version": 1,
        "diagnosis": diagnosis,
        "diagnosis_basis": "SUPPLIED_SANITIZED_OBSERVATIONS_ONLY",
        "observations": {
            "process_inventory": process,
            "connection_stages": stages,
            "authorization": authorization,
            "accepted_shares": shares,
            "account_match": account,
        },
        "next_action": next_action,
        "read_only_classifier": True,
        "network_access_performed": False,
        "credentials_read": False,
        "settings_changed": False,
        "miner_started_or_stopped": False,
        "real_mining_verified": False,
        "brain_work_attribution_verified": False,
        "revenue_verified": False,
        "limitations": [
            "Missing or untrusted observations are not treated as success.",
            "No known local process does not rule out an external ASIC or remote miner.",
            "A reported accepted share does not independently prove Brain generated the work.",
            "This classifier performs no DNS, TCP, TLS, Stratum, or pool API requests.",
        ],
    }
