from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class FailureDecision:
    classification: str
    retryable: bool
    delay_seconds: int
    repair_action: str

class FailurePolicy:
    RETRYABLE={"EXECUTION_TRANSIENT","RESOURCE_BUSY","BACKEND_UNAVAILABLE","VERIFICATION_TRANSIENT"}
    NON_RETRYABLE={"INVALID_INPUT","POLICY_BLOCKED","UNSUPPORTED_CAPABILITY","VERIFICATION_FATAL"}

    def classify(self,error,status=None):
        e=str(error or "").upper()
        if "OFFLINE" in e or "TIMEOUT" in e: return "EXECUTION_TRANSIENT"
        if "NO_CAPABLE_RESOURCE" in e or "INSUFFICIENT" in e: return "RESOURCE_BUSY"
        if "QEMU_NOT_AVAILABLE" in e or "BACKEND" in e: return "BACKEND_UNAVAILABLE"
        if "VERIFY" in e or "QC" in e: return "VERIFICATION_TRANSIENT"
        if "POLICY" in e or "UNSUPPORTED" in e: return "POLICY_BLOCKED" if "POLICY" in e else "UNSUPPORTED_CAPABILITY"
        return "EXECUTION_TRANSIENT" if status not in {"INVALID_INPUT"} else "INVALID_INPUT"

    def decide(self,error,attempt,max_attempts):
        kind=self.classify(error)
        retryable=kind in self.RETRYABLE and int(attempt)<int(max_attempts)
        delay=min(300,2**max(0,int(attempt)-1)) if retryable else 0
        repair={"RESOURCE_BUSY":"WAIT_FOR_RESOURCE","BACKEND_UNAVAILABLE":"SELECT_FALLBACK",
                "VERIFICATION_TRANSIENT":"REVERIFY","EXECUTION_TRANSIENT":"RETRY_EXECUTION"}.get(kind,"BLOCK")
        return FailureDecision(kind,retryable,delay,repair)
