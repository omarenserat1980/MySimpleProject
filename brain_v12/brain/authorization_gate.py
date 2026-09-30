"""Fail-closed authorization gate for Brain side effects.

Inspired by open-source policy-as-code and human-in-the-loop patterns.
This module is Brain-native and does not copy third-party source.
"""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path

class AuthorizationGate:
    def __init__(self,path="brain6_artifacts/authorization/events.jsonl"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)

    def decide(self, action, principal="brain", risk="low", resource=None,
               requires_owner_approval=False, approved=False, approval_id=None):
        sensitive={"move_money","withdraw","external_submit","publish_external","contract","change_policy"}
        if action in sensitive and not (requires_owner_approval and approved and approval_id):
            decision="HUMAN_REVIEW"
            reason="explicit_owner_approval_required"
        elif action not in {"discover","plan","select_backend","execute","verify","repair","retry","deliver"} and action not in sensitive:
            decision="DENY"; reason="unknown_action"
        else:
            decision="ALLOW"; reason="policy_match"
        event={
            "ts":time.time(),"action":action,"principal":principal,"risk":risk,
            "resource":resource or {},"decision":decision,"reason":reason,
            "approval_id":approval_id
        }
        event["decision_hash"]=hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest()
        with self.path.open("a",encoding="utf-8") as f:f.write(json.dumps(event)+"\n")
        return event

if __name__=="__main__":
    print(json.dumps(AuthorizationGate().decide("move_money"),indent=2))
