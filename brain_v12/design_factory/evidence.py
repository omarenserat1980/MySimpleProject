"""Fail-closed evidence classification helpers."""
ALLOWED_STATUSES={"PLANNED","DESIGNED","IMPLEMENTED","SIMULATED","TESTED","VERIFIED","BLOCKED","FAILED","HARDWARE_VERIFIED","MANUFACTURED_VERIFIED","REVENUE_VERIFIED"}
REAL_WORLD_STATUSES={"HARDWARE_VERIFIED","MANUFACTURED_VERIFIED","REVENUE_VERIFIED"}

def classify_evidence(status:str,*,simulation_only:bool=False,evidence_present:bool=False,independent_review:bool=False)->dict:
    """Validate claim level without upgrading status based on intent alone."""
    if status not in ALLOWED_STATUSES: raise ValueError(f"Unknown evidence status: {status}")
    if status in {"VERIFIED",*REAL_WORLD_STATUSES} and not evidence_present:
        return {"accepted":False,"status":"BLOCKED","reason":"required evidence is absent"}
    if status in REAL_WORLD_STATUSES and simulation_only:
        return {"accepted":False,"status":"BLOCKED","reason":"simulation cannot prove a real-world claim"}
    if status in {"VERIFIED",*REAL_WORLD_STATUSES} and not independent_review:
        return {"accepted":False,"status":"BLOCKED","reason":"independent review is required for this claim level"}
    if status=="SIMULATED" and not simulation_only:
        return {"accepted":False,"status":"BLOCKED","reason":"simulation status requires explicit simulation_only=true"}
    return {"accepted":True,"status":status,"reason":"classification accepted at requested evidence level"}
