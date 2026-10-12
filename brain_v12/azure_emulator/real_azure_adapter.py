from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol
from .real_adapter_contract import LaunchPlan, FreeOnlyGuard
from .free_cost_gate import require_free_entitlement
import hashlib, json, time
from .handoff import HandoffLedger

class AzureSDK(Protocol):
    def preflight(self, plan: LaunchPlan) -> dict[str,Any]: ...
    def provision(self, plan: LaunchPlan) -> dict[str,Any]: ...
    def verify(self, plan: LaunchPlan) -> dict[str,Any]: ...
    def destroy(self, plan: LaunchPlan) -> dict[str,Any]: ...

@dataclass
class RealAzureAdapter:
    sdk: AzureSDK
    ledger: HandoffLedger
    allow_real: bool = False

    def preflight(self, plan: LaunchPlan, handoff: dict[str,Any], evidence: dict[str,Any] | None = None) -> dict[str,Any]:
        if not self.allow_real:
            return {"ok":False,"status":"REAL_AZURE_DISABLED","reason":"REAL_AZURE_EXPLICIT_ENABLE_REQUIRED"}
        if plan.free_only is not True:
            return {"ok":False,"status":"FREE_ONLY_REQUIRED"}
        self._validate_handoff(handoff, plan, evidence)
        result=self.sdk.preflight(plan)
        FreeOnlyGuard.require_free(result)
        require_free_entitlement(result)
        return {"ok":True,"status":"REAL_AZURE_PREFLIGHT_VERIFIED","preflight":result}

    def provision(self, plan: LaunchPlan, handoff: dict[str,Any], evidence: dict[str,Any] | None = None) -> dict[str,Any]:
        pre=self.preflight(plan,handoff,evidence)
        if not pre["ok"]: raise RuntimeError(pre["reason"])
        self.ledger.consume(handoff["certificate_id"])
        result=self.sdk.provision(plan)
        if not result.get("ok"):
            raise RuntimeError("REAL_AZURE_PROVISION_FAILED")
        return {"ok":True,"status":"REAL_AZURE_PROVISIONED","result":result}

    def verify(self, plan: LaunchPlan) -> dict[str,Any]:
        result=self.sdk.verify(plan)
        if not result.get("ok"): raise RuntimeError("REAL_AZURE_VERIFY_FAILED")
        return result

    def destroy(self, plan: LaunchPlan) -> dict[str,Any]:
        return self.sdk.destroy(plan)

    @staticmethod
    def _validate_handoff(handoff:dict[str,Any], plan: LaunchPlan, evidence: dict[str,Any] | None = None)->None:
        if handoff.get("schema")!="BRAIN-REAL-AZURE-HANDOFF-3": raise RuntimeError("HANDOFF_SCHEMA_INVALID")
        if handoff.get("single_use") is not True: raise RuntimeError("HANDOFF_SINGLE_USE_REQUIRED")
        if handoff.get("free_only") is not True: raise RuntimeError("HANDOFF_FREE_ONLY_REQUIRED")
        if handoff.get("provider")!="brain-emulated-azure": raise RuntimeError("HANDOFF_PROVIDER_INVALID")
        if not handoff.get("certificate_id"): raise RuntimeError("HANDOFF_CERTIFICATE_REQUIRED")
        if float(handoff.get("expires_at", 0)) <= time.time(): raise RuntimeError("HANDOFF_EXPIRED")
        canonical_plan = {"location": plan.location, "vm_size": plan.vm_size, "os_image": plan.os_image, "free_only": plan.free_only}
        plan_hash = hashlib.sha256(json.dumps(canonical_plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if handoff.get("plan_sha256") != plan_hash: raise RuntimeError("HANDOFF_PLAN_HASH_MISMATCH")
        if evidence is None: raise RuntimeError("HANDOFF_EVIDENCE_REQUIRED")
        evidence_hash = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if handoff.get("evidence_sha256") != evidence_hash: raise RuntimeError("HANDOFF_EVIDENCE_HASH_MISMATCH")
