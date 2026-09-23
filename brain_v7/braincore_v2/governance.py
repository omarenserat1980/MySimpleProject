"""Safety and financial governance for the external Electronic Brain runtime.
This module classifies and audits actions but never grants money-moving, credential,
legal-signature, or destructive permissions automatically.
"""
from __future__ import annotations
import hashlib, json, os, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(os.getenv("BRAIN_AUDIT_PATH", "brain_audit.jsonl"))
DENY_ACTIONS = frozenset({
    "transfer_money","withdraw_money","borrow_money","place_order",
    "trade_real_money","open_bank_account","sign_contract",
    "publish_irreversible_legal_statement","delete_repository",
    "rotate_credentials","read_secret",
})
@dataclass(frozen=True)
class PolicyDecision:
    action: str
    allowed: bool
    requires_approval: bool
    risk: str
    reason: str
def evaluate_action(action: str, *, amount_jod: float=0.0, irreversible: bool=False) -> PolicyDecision:
    a=str(action).strip().lower()
    if a in DENY_ACTIONS:
        return PolicyDecision(a,False,True,"CRITICAL","Action is outside autonomous authority.")
    if amount_jod>0 or irreversible:
        return PolicyDecision(a,True,True,"HIGH","Financial or irreversible effect requires human approval.")
    if a in {"web_publish","send_message","create_lead","submit_job"}:
        return PolicyDecision(a,True,True,"MEDIUM","External side effect requires approval in this runtime.")
    return PolicyDecision(a,True,False,"LOW","Read-only or reversible computation.")
def evaluate_authorized_action(action: str, *, user_authorized: bool = False) -> PolicyDecision:
    """Evaluate a money-moving action after explicit user authorization.

    Autonomous authority remains disabled. This path only permits the action
    to proceed to the real provider when the caller proves that the user has
    explicitly authorized the exact operation; provider confirmation is still
    required before success is reported.
    """
    a = str(action).strip().lower()
    if a in {"transfer_money", "withdraw_money"}:
        if not user_authorized:
            return PolicyDecision(a, False, True, "CRITICAL",
                                  "Explicit user authorization is required.")
        return PolicyDecision(a, True, False, "HIGH",
                              "User-authorized provider execution; confirmation required.")
    return evaluate_action(a)

def append_audit(event: str, payload: dict[str,Any]) -> dict[str,Any]:
    AUDIT_PATH.parent.mkdir(parents=True,exist_ok=True)
    previous=""
    if AUDIT_PATH.is_file():
        try: previous=json.loads(AUDIT_PATH.read_text(encoding="utf-8").splitlines()[-1]).get("hash","")
        except Exception: previous=""
    record={"ts":time.time(),"event":str(event),"payload":payload,"previous_hash":previous}
    body=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    record["hash"]=hashlib.sha256(body.encode("utf-8")).hexdigest()
    with AUDIT_PATH.open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False)+"\n")
    return record
def policy_snapshot() -> dict[str,Any]:
    return {"autonomous_money_movement":False,"autonomous_contract_signing":False,
            "autonomous_secret_access":False,"destructive_repository_actions":False,"audit_chain":True}
