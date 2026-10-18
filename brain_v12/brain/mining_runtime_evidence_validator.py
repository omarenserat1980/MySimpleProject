"""Read-only structural and integrity validation for mining evidence.

No collection or network access occurs. A matching SHA-256 detects payload changes
relative to this envelope; it does not authenticate the source or prove mining.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

SCHEMA_VERSION = 1
STAGE_STATES = {"PASS", "FAIL", "NOT_RUN", "UNKNOWN"}
PROCESS_STATES = {"FOUND", "NONE_FOUND", "UNAVAILABLE", "UNKNOWN"}
AUTH_STATES = {"ACCEPTED", "REJECTED", "NOT_TESTED", "UNKNOWN"}
SHARE_STATES = {"ACCEPTED_REPORTED", "NONE_REPORTED", "NOT_CHECKED", "UNKNOWN"}
ACCOUNT_STATES = {"MATCH", "MISMATCH", "NOT_CHECKED", "UNKNOWN"}

_REQUIRED_SOURCE = {"kind", "collector_version", "host_id"}
_REQUIRED_COLLECTION = {
    "mode", "network_probes_performed", "credentials_read",
    "settings_changed", "miner_started_or_stopped",
}
_REQUIRED_OBSERVATIONS = {
    "process_inventory", "dns", "tcp", "tls", "stratum",
    "authorization", "accepted_shares", "account_match",
}
_SECRET_KEYS = {
    "password", "token", "access_token", "authorization_payload",
    "secret", "private_key", "pool_url", "raw_response",
}


def _is_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                return True
            normalized = key.lower()
            if normalized in _SECRET_KEYS or any(
                marker in normalized
                for marker in ("password", "token", "private_key", "authorization_payload", "raw_response")
            ):
                return True
            if _contains_forbidden_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def canonical_payload_sha256(evidence: dict[str, Any]) -> str:
    """Hash the canonical JSON envelope excluding its integrity block."""
    payload = {key: value for key, value in evidence.items() if key != "integrity"}
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_mining_runtime_evidence(evidence: Any) -> dict[str, Any]:
    """Validate structure and payload hash, without authenticating the source."""
    errors: list[str] = []
    hash_verified = False
    if not isinstance(evidence, dict):
        return {
            "schema_version": SCHEMA_VERSION,
            "valid": False,
            "errors": ["EVIDENCE_MUST_BE_OBJECT"],
            "source_authenticated": False,
            "integrity_hash_verified": False,
            "real_mining_verified": False,
            "brain_work_attribution_verified": False,
            "revenue_verified": False,
            "network_access_performed": False,
        }

    if evidence.get("schema_version") != SCHEMA_VERSION:
        errors.append("UNSUPPORTED_SCHEMA_VERSION")
    if not isinstance(evidence.get("evidence_id"), str) or not evidence["evidence_id"].strip():
        errors.append("EVIDENCE_ID_REQUIRED")

    source = evidence.get("source")
    if not isinstance(source, dict) or not _REQUIRED_SOURCE.issubset(source):
        errors.append("SOURCE_FIELDS_MISSING")
    elif any(not isinstance(source.get(k), str) or not source[k].strip() for k in _REQUIRED_SOURCE):
        errors.append("SOURCE_FIELDS_INVALID")

    if not _is_utc_timestamp(evidence.get("observed_at")):
        errors.append("OBSERVED_AT_MUST_BE_UTC_ISO8601")

    collection = evidence.get("collection")
    if not isinstance(collection, dict) or not _REQUIRED_COLLECTION.issubset(collection):
        errors.append("COLLECTION_FIELDS_MISSING")
    else:
        if collection.get("mode") != "read_only":
            errors.append("COLLECTION_MODE_MUST_BE_READ_ONLY")
        for flag in ("network_probes_performed", "credentials_read", "settings_changed", "miner_started_or_stopped"):
            if collection.get(flag) is not False:
                errors.append("UNSAFE_COLLECTION_FLAG:" + flag)

    observations = evidence.get("observations")
    if not isinstance(observations, dict) or not _REQUIRED_OBSERVATIONS.issubset(observations):
        errors.append("OBSERVATION_FIELDS_MISSING")
    else:
        allowed = {
            "process_inventory": PROCESS_STATES,
            "dns": STAGE_STATES,
            "tcp": STAGE_STATES,
            "tls": STAGE_STATES,
            "stratum": STAGE_STATES,
            "authorization": AUTH_STATES,
            "accepted_shares": SHARE_STATES,
            "account_match": ACCOUNT_STATES,
        }
        for key, values in allowed.items():
            if observations.get(key) not in values:
                errors.append("INVALID_OBSERVATION:" + key)

    integrity = evidence.get("integrity")
    if not isinstance(integrity, dict) or not isinstance(integrity.get("payload_sha256"), str):
        errors.append("INTEGRITY_HASH_MISSING")
    else:
        supplied_hash = integrity["payload_sha256"]
        if not re.fullmatch(r"[0-9a-fA-F]{64}", supplied_hash):
            errors.append("INTEGRITY_HASH_INVALID")
        else:
            calculated_hash = canonical_payload_sha256(evidence)
            hash_verified = supplied_hash.lower() == calculated_hash
            if not hash_verified:
                errors.append("INTEGRITY_HASH_MISMATCH")

    if _contains_forbidden_key(evidence):
        errors.append("FORBIDDEN_SECRET_LIKE_FIELD")

    return {
        "schema_version": SCHEMA_VERSION,
        "valid": not errors,
        "errors": errors,
        "source_authenticated": False,
        "integrity_hash_verified": hash_verified,
        "real_mining_verified": False,
        "brain_work_attribution_verified": False,
        "revenue_verified": False,
        "network_access_performed": False,
        "credentials_read": False,
        "settings_changed": False,
        "miner_started_or_stopped": False,
        "limitations": [
            "A matching SHA-256 detects payload changes but does not authenticate the source.",
            "A signature is not verified by this validator.",
            "Pool-side shares, Brain work attribution, hashrate, and revenue require separate evidence gates.",
        ],
    }
