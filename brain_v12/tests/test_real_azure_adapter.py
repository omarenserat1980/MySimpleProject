from brain_v12.azure_emulator.real_azure_adapter import RealAzureAdapter
from brain_v12.azure_emulator.real_adapter_contract import LaunchPlan
from brain_v12.azure_emulator.handoff import HandoffLedger

class FakeSDK:
    def __init__(self): self.calls=[]
    def preflight(self,plan): self.calls.append("preflight"); return {"ok":True,"free_capacity":True,"estimated_cost":0}
    def provision(self,plan): self.calls.append("provision"); return {"ok":True,"vm_id":"real-test"}
    def verify(self,plan): self.calls.append("verify"); return {"ok":True}
    def destroy(self,plan): self.calls.append("destroy"); return {"ok":True}

def test_real_adapter_is_disabled_by_default():
    sdk=FakeSDK(); a=RealAzureAdapter(sdk,HandoffLedger(":memory:"))
    p=LaunchPlan("eastus","B2ats_v2")
    try: a.provision(p,{"schema":"BRAIN-REAL-AZURE-HANDOFF-3","single_use":True,"free_only":True,"provider":"brain-emulated-azure","certificate_id":"x"})
    except RuntimeError as e: assert str(e)=="REAL_AZURE_EXPLICIT_ENABLE_REQUIRED"
    else: raise AssertionError("real Azure path enabled by default")
    assert sdk.calls==[]

def test_real_adapter_requires_zero_cost_preflight():
    class Paid(FakeSDK):
        def preflight(self,plan): return {"ok":True,"free_capacity":True,"estimated_cost":1}
    a=RealAzureAdapter(Paid(),HandoffLedger(":memory:"),allow_real=True)
    p=LaunchPlan("eastus","B2ats_v2")
    try: a.preflight(p,{"schema":"BRAIN-REAL-AZURE-HANDOFF-3","single_use":True,"free_only":True,"provider":"brain-emulated-azure","certificate_id":"x"})
    except RuntimeError as e: assert str(e)=="PAID_RESOURCE_BLOCKED"
    else: raise AssertionError("paid path accepted")
