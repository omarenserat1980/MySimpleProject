"""Recovery gate for durable mission state."""
from dataclasses import dataclass
from .mission_lifecycle import MissionState
from .mission_runtime import MissionRuntime

class RecoveryStatus:
    HEALTHY="HEALTHY"
    RECOVERABLE="RECOVERABLE"
    CORRUPTED="CORRUPTED"

@dataclass(frozen=True)
class RecoveryReport:
    status:str
    state:MissionState
    record_count:int
    chain_valid:bool
    reason:str

def inspect(runtime:MissionRuntime)->RecoveryReport:
    records=runtime.history()
    if not records:
        return RecoveryReport(RecoveryStatus.HEALTHY,MissionState.PLANNED,0,True,"new mission")
    try:
        valid=runtime.verify_chain()
        state=runtime.state()
    except Exception as exc:
        return RecoveryReport(RecoveryStatus.CORRUPTED,MissionState.HOLD,len(records),False,str(exc))
    if not valid:
        return RecoveryReport(RecoveryStatus.CORRUPTED,MissionState.HOLD,len(records),False,"evidence chain invalid")
    if state in {MissionState.EXECUTING,MissionState.VERIFYING}:
        return RecoveryReport(RecoveryStatus.RECOVERABLE,state,len(records),True,"mission interrupted during side-effecting phase")
    return RecoveryReport(RecoveryStatus.HEALTHY,state,len(records),True,"chain verified")
