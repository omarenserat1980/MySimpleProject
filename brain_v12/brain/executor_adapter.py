from __future__ import annotations
from dataclasses import dataclass
from time import time

@dataclass
class ExecutionResult:
    ok: bool
    status: str
    executor_id: str
    result: dict
    started_at: float
    finished_at: float

class ExecutorAdapter:
    """Stable interface between Brain scheduling and execution backends."""
    executor_type="generic"

    def __init__(self, executor_id):
        self.executor_id=executor_id

    def capabilities(self):
        raise NotImplementedError

    def execute(self, task):
        raise NotImplementedError

class BladeExecutorAdapter(ExecutorAdapter):
    executor_type="blade"

    def __init__(self, blade):
        super().__init__(blade.blade_id)
        self.blade=blade

    def capabilities(self):
        return set(self.blade.capabilities)

    def execute(self, task):
        started=time()
        try:
            result=self.blade.execute(task.program,getattr(task,'max_cycles',10000))
            return ExecutionResult(True,"COMPLETED",self.executor_id,result,started,time())
        except Exception as exc:
            return ExecutionResult(False,"FAILED",self.executor_id,{"error":str(exc)},started,time())


class QemuWindowsExecutorAdapter(ExecutorAdapter):
    executor_type="qemu-windows"

    def __init__(self, backend):
        super().__init__("qemu-windows")
        self.backend=backend

    def capabilities(self):
        return {"x86_64","windows-server-2025","network","storage"}

    def execute(self, task):
        started=time()
        try:
            result=self.backend.run(
                install=getattr(task,"install",True),
                timeout=getattr(task,"timeout",300),
            )
            ok=bool(result.get("guest",{}).get("boot_verified"))
            status="GUEST_BOOT_VERIFIED" if ok else result.get("status","QEMU_FAILED")
            return ExecutionResult(ok,status,self.executor_id,result,started,time())
        except Exception as exc:
            return ExecutionResult(False,"QEMU_EXECUTOR_ERROR",self.executor_id,{"error":str(exc)},started,time())
