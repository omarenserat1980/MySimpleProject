"""Idempotency gate for mission side-effect execution."""
from dataclasses import dataclass
import hashlib

@dataclass(frozen=True)
class ExecutionIntent:
    mission_fingerprint:str
    action:str
    parameters_fingerprint:str

    @property
    def execution_key(self)->str:
        raw=f"{self.mission_fingerprint}:{self.action}:{self.parameters_fingerprint}".encode()
        return hashlib.sha256(raw).hexdigest()

class IdempotencyGate:
    def __init__(self):
        self._completed=set()
        self._claimed=set()

    def key(self,intent:ExecutionIntent)->str:
        return intent.execution_key

    def claim(self,intent:ExecutionIntent)->str:
        key=self.key(intent)
        if key in self._completed:
            raise RuntimeError("execution already completed")
        if key in self._claimed:
            raise RuntimeError("execution already claimed")
        self._claimed.add(key)
        return key

    def complete(self,intent:ExecutionIntent)->str:
        key=self.key(intent)
        if key not in self._claimed:
            raise RuntimeError("execution was not claimed")
        self._claimed.remove(key)
        self._completed.add(key)
        return key

    def is_completed(self,intent:ExecutionIntent)->bool:
        return self.key(intent) in self._completed
