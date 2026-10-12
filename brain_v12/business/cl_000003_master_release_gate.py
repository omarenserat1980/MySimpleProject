"""Evidence-bound release contract with artifact binding."""
from __future__ import annotations
import hashlib
import json
from typing import Any

REQUIRED=("technical","cinematic","rights","legal_policy")
IDENTITY_REQUIRED=("film_id","film_version","production_run")
EVIDENCE_REQUIRED=("evidence_ref","evidence_sha256","reviewed_artifact_sha256")

def _digest(value: Any)->str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def _prefix(identity):
    return f"{identity['film_id']}/{identity['film_version']}/{identity['production_run']}/"

def decide(evidence: dict[str,Any])->dict[str,Any]:
    failures=[]; states={}
    identity={k:str(evidence.get(k) or "").strip() for k in IDENTITY_REQUIRED}
    for k,v in identity.items():
        if not v: failures.append(f"{k.upper()}_REQUIRED")
    prefix=_prefix(identity) if not failures else ""
    artifact_sha=str(evidence.get("artifact_sha256") or "").strip().lower()
    if not artifact_sha: failures.append("ARTIFACT_SHA256_REQUIRED")
    elif len(artifact_sha)!=64: failures.append("ARTIFACT_SHA256_INVALID")
    for key in REQUIRED:
        item=evidence.get(key)
        passed=isinstance(item,dict) and item.get("passed") is True
        states[key]="PASS" if passed else "FAIL"
        if not passed:
            failures.append(f"{key.upper()}_PASS_REQUIRED"); continue
        for field in EVIDENCE_REQUIRED:
            if not str(item.get(field) or "").strip():
                failures.append(f"{key.upper()}_{field.upper()}_REQUIRED")
        ref=str(item.get("evidence_ref") or "").strip()
        if prefix and ref and not ref.startswith(prefix):
            failures.append(f"{key.upper()}_EVIDENCE_IDENTITY_MISMATCH")
        supplied=str(item.get("evidence_sha256") or "").strip().lower()
        reviewed=str(item.get("reviewed_artifact_sha256") or "").strip().lower()
        if supplied and len(supplied)!=64: failures.append(f"{key.upper()}_EVIDENCE_HASH_INVALID")
        if reviewed and len(reviewed)!=64: failures.append(f"{key.upper()}_ARTIFACT_HASH_INVALID")
        if artifact_sha and reviewed and reviewed!=artifact_sha:
            failures.append(f"{key.upper()}_ARTIFACT_HASH_MISMATCH")
    release=not failures
    decision={"status":"MASTER_RELEASE_PASS" if release else "DO_NOT_PUBLISH","publish_authorized":release,
              "gates":states,"failures":failures,"next_action":"PUBLISH" if release else "DIAGNOSE_REWORK_REPLACE",
              "identity":identity,"artifact_sha256":artifact_sha}
    decision["decision_sha256"]=_digest(decision)
    return decision
