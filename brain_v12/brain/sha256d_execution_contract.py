"""Canonical, fail-closed result contract for Electronic Brain SHA-256d layers.

A PASS means only that the named local/software layer supplied its required
evidence. It never means live pool activity, physical ASIC operation, payout,
or revenue. Local digests are integrity checks, not signatures/authentication.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any

CONTRACT_VERSION = "1.0"
STATUSES = {"PASS", "FAIL", "BLOCKED", "CANCELLED", "TIMEOUT", "NOT_RUN"}
ARABIC_LAYER_NAMES = {
    "cpu_reference": "مرجع SHA-256d البرمجي",
    "rtl_simulator": "محاكي RTL الرقمي",
    "mcp_contract": "واجهة MCP وعقد الأدلة",
    "pool_activity": "اتصال المسبح والمشاركات",
    "revenue": "إثبات الإيراد",
}
ARABIC_STATUS_NAMES = {
    "PASS": "اجتاز الفحص المحلي",
    "FAIL": "فشل الفحص",
    "BLOCKED": "محظور أو الأداة غير متاحة",
    "CANCELLED": "أُلغي التنفيذ",
    "TIMEOUT": "انتهت المهلة",
    "NOT_RUN": "لم يُنفذ",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_digest(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("evidence_sha256", None)
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _pass_evidence_failures(layer: str, evidence: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not evidence:
        return ["PASS_WITHOUT_EVIDENCE"]
    if layer == "cpu_reference":
        count = evidence.get("hashes_completed")
        elapsed = evidence.get("elapsed_seconds")
        rate = evidence.get("hashrate_hs")
        digest = evidence.get("last_digest_hex")
        if evidence.get("execution_scope") != "HOST_CPU_SOFTWARE_ONLY":
            failures.append("CPU_SCOPE_MISSING")
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            failures.append("CPU_HASH_COUNT_INVALID")
        for name, value in (("elapsed_seconds", elapsed), ("hashrate_hs", rate)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                failures.append("CPU_" + name.upper() + "_INVALID")
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in digest):
            failures.append("CPU_DIGEST_INVALID")
    elif layer == "rtl_simulator":
        if not isinstance(evidence.get("case"), str) or not evidence.get("case"):
            failures.append("RTL_CASE_MISSING")
        if not isinstance(evidence.get("top_module"), str) or not evidence.get("top_module"):
            failures.append("RTL_TOP_MODULE_MISSING")
        if not isinstance(evidence.get("source_sha256"), dict) or not evidence.get("source_sha256"):
            failures.append("RTL_SOURCE_HASHES_MISSING")
        for phase in ("compile", "simulation"):
            result = evidence.get(phase)
            if not isinstance(result, dict) or result.get("status") != "PASS" or result.get("exit_code") != 0:
                failures.append("RTL_" + phase.upper() + "_NOT_PASS")
        if not isinstance(evidence.get("required_success_marker"), str) or not evidence.get("required_success_marker"):
            failures.append("RTL_SUCCESS_MARKER_MISSING")
        if evidence.get("success_marker_found") is not True:
            failures.append("RTL_SUCCESS_MARKER_NOT_FOUND")
        if evidence.get("execution_scope") != "LOCAL_RTL_SIMULATION_ONLY":
            failures.append("RTL_SCOPE_MISSING")
    return failures


def make_layer_result(
    *,
    layer: str,
    status: str,
    evidence: dict[str, Any] | None = None,
    error_code: str | None = None,
    started_at_utc: str | None = None,
    finished_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build the shared result envelope. PASS without concrete evidence fails closed."""
    if status not in STATUSES:
        status, error_code = "FAIL", "INVALID_STATUS"
    evidence = evidence if isinstance(evidence, dict) else {}
    if status == "PASS":
        evidence_failures = _pass_evidence_failures(layer, evidence)
        if evidence_failures:
            status, error_code = "FAIL", "PASS_EVIDENCE_INCOMPLETE:" + ",".join(evidence_failures)
    record: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "layer": layer,
        "layer_ar": ARABIC_LAYER_NAMES.get(layer, layer),
        "status": status,
        "status_ar": ARABIC_STATUS_NAMES[status],
        "started_at_utc": started_at_utc or utc_now(),
        "finished_at_utc": finished_at_utc or utc_now(),
        "evidence": evidence,
        "error_code": error_code,
        "claims": {
            "rtl_verified": layer == "rtl_simulator" and status == "PASS",
            "cpu_reference_verified": layer == "cpu_reference" and status == "PASS",
            "pool_connected": False,
            "accepted_share_verified": False,
            "physical_asic_verified": False,
            "payout_verified": False,
            "revenue_verified": False,
        },
        "evidence_authentication": "LOCAL_CANONICAL_DIGEST_ONLY_NOT_AUTHENTICATION",
    }
    record["evidence_sha256"] = canonical_digest(record)
    return record


def validate_layer_result(record: Any) -> dict[str, Any]:
    """Validate envelope shape and digest; never upgrade a result's status."""
    failures: list[str] = []
    if not isinstance(record, dict):
        return {"valid": False, "failures": ["RECORD_NOT_OBJECT"]}
    if record.get("contract_version") != CONTRACT_VERSION:
        failures.append("UNSUPPORTED_CONTRACT_VERSION")
    if record.get("status") not in STATUSES:
        failures.append("INVALID_STATUS")
    if not isinstance(record.get("layer"), str) or not record["layer"]:
        failures.append("LAYER_MISSING")
    if not isinstance(record.get("evidence"), dict):
        failures.append("EVIDENCE_NOT_OBJECT")
    if record.get("status") == "PASS" and isinstance(record.get("evidence"), dict):
        failures.extend(_pass_evidence_failures(record.get("layer", ""), record["evidence"]))
    digest = record.get("evidence_sha256")
    if not isinstance(digest, str) or digest != canonical_digest(record):
        failures.append("EVIDENCE_DIGEST_MISMATCH")
    claims = record.get("claims")
    if not isinstance(claims, dict):
        failures.append("CLAIMS_MISSING")
    elif any(claims.get(key) is True for key in (
        "pool_connected", "accepted_share_verified", "physical_asic_verified",
        "payout_verified", "revenue_verified",
    )):
        failures.append("UNSUPPORTED_EXTERNAL_CLAIM")
    return {"valid": not failures, "failures": failures, "status": record.get("status")}


def layer_status_snapshot() -> dict[str, Any]:
    """Arabic UI/MCP status template; NOT_RUN is intentional until a layer is run."""
    layers = [
        make_layer_result(layer="cpu_reference", status="NOT_RUN"),
        make_layer_result(layer="rtl_simulator", status="NOT_RUN"),
        make_layer_result(layer="mcp_contract", status="NOT_RUN", error_code="MCP_INTEGRATION_TEST_NOT_RUN"),
        make_layer_result(layer="pool_activity", status="BLOCKED", error_code="INDEPENDENT_POOL_EVIDENCE_REQUIRED"),
        make_layer_result(layer="revenue", status="BLOCKED", error_code="INDEPENDENT_PAYOUT_EVIDENCE_REQUIRED"),
    ]
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "title_ar": "حالة طبقات SHA-256d",
        "layers": layers,
        "summary_ar": "حالة الواجهة والعقد فقط؛ لم يتم تشغيل محاكي RTL أو إثبات تعدين خارجي من هذا الطلب.",
        "live_mining": False,
        "pool_connected": False,
        "accepted_share_verified": False,
        "physical_asic_verified": False,
        "revenue_verified": False,
    }
