import hashlib, json, time

from brain_v12.azure_emulator.real_azure_adapter import RealAzureAdapter
from brain_v12.azure_emulator.real_adapter_contract import LaunchPlan
from brain_v12.azure_emulator.handoff import HandoffLedger


def evidence():
    return {"schema": "BRAIN-AZURE-EMULATOR-EVIDENCE-1", "ok": True, "provider": "brain-emulated-azure", "vm": {"id": "vm"}}


def handoff(plan, ev):
    canonical_plan = {"location": plan.location, "vm_size": plan.vm_size, "os_image": plan.os_image, "free_only": plan.free_only}
    return {
        "schema": "BRAIN-REAL-AZURE-HANDOFF-3", "single_use": True, "free_only": True,
        "provider": "brain-emulated-azure", "certificate_id": "x",
        "issued_at": time.time(), "expires_at": time.time() + 300,
        "plan_sha256": hashlib.sha256(json.dumps(canonical_plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "evidence_sha256": hashlib.sha256(json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }


class FakeSDK:
    def __init__(self, pre=None): self.calls=[]; self.pre=pre or {"ok":True,"free_capacity":True,"estimated_cost":0,"free_entitlement_verified":True,"free_hours_remaining":100,"requested_free_hours":1,"dependent_resources_cost_verified_zero":True,"spending_limit_protected":True}
    def preflight(self,plan): self.calls.append("preflight"); return self.pre
    def provision(self,plan): self.calls.append("provision"); return {"ok":True,"vm_id":"real-test"}
    def verify(self,plan): self.calls.append("verify"); return {"ok":True}
    def destroy(self,plan): self.calls.append("destroy"); return {"ok":True}


def test_real_adapter_is_disabled_by_default():
    sdk=FakeSDK(); a=RealAzureAdapter(sdk,HandoffLedger(":memory:"))
    p=LaunchPlan("eastus","B2ats_v2"); ev=evidence()
    try: a.provision(p,handoff(p,ev),ev)
    except RuntimeError as e: assert str(e)=="REAL_AZURE_EXPLICIT_ENABLE_REQUIRED"
    else: raise AssertionError("real Azure path enabled by default")
    assert sdk.calls==[]


def test_real_adapter_requires_zero_cost_preflight():
    paid=FakeSDK({"ok":True,"free_capacity":True,"estimated_cost":1,"free_entitlement_verified":True,"free_hours_remaining":100,"requested_free_hours":1,"dependent_resources_cost_verified_zero":True,"spending_limit_protected":True})
    a=RealAzureAdapter(paid,HandoffLedger(":memory:"),allow_real=True)
    p=LaunchPlan("eastus","B2ats_v2"); ev=evidence()
    try: a.preflight(p,handoff(p,ev),ev)
    except RuntimeError as e: assert str(e)=="PAID_RESOURCE_BLOCKED"
    else: raise AssertionError("paid path accepted")


def test_real_adapter_blocks_unproven_free_entitlement():
    sdk=FakeSDK({"ok":True,"free_capacity":True,"estimated_cost":0,"free_entitlement_verified":False})
    a=RealAzureAdapter(sdk,HandoffLedger(":memory:"),allow_real=True)
    p=LaunchPlan("eastus","B2ats_v2"); ev=evidence()
    try: a.preflight(p,handoff(p,ev),ev)
    except RuntimeError as e: assert str(e)=="FREE_ENTITLEMENT_NOT_VERIFIED"
    else: raise AssertionError("unproven free entitlement accepted")


def test_real_adapter_blocks_handoff_hash_tampering():
    sdk=FakeSDK(); a=RealAzureAdapter(sdk,HandoffLedger(":memory:"),allow_real=True)
    p=LaunchPlan("eastus","B2ats_v2"); ev=evidence(); h=handoff(p,ev); h["plan_sha256"]="tampered"
    try: a.preflight(p,h,ev)
    except RuntimeError as e: assert str(e)=="HANDOFF_PLAN_HASH_MISMATCH"
    else: raise AssertionError("tampered handoff accepted")
