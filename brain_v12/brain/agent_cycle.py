"""Bounded Brain agent cycle: plan -> act -> observe -> verify -> learn.

This is a small Brain-native control loop, deliberately dependency-free. The
caller supplies the actual action function, keeping external effects explicit.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any

@dataclass
class CycleResult:
    success: bool
    attempts: int
    events: list[dict] = field(default_factory=list)
    output: Any = None

def run(task: str, action: Callable[[str, int], Any],
        verify: Callable[[Any], bool], max_attempts: int = 3) -> CycleResult:
    attempts=max(1,min(int(max_attempts),5))
    events=[]
    for attempt in range(1,attempts+1):
        try:
            output=action(task,attempt)
            ok=bool(verify(output))
            events.append({"phase":"observe","attempt":attempt,"verified":ok})
            if ok:
                events.append({"phase":"learn","outcome":"success","attempt":attempt})
                return CycleResult(True,attempt,events,output)
            events.append({"phase":"learn","outcome":"retry","attempt":attempt})
        except Exception as exc:
            events.append({"phase":"observe","attempt":attempt,"verified":False,
                           "error":str(exc)[:240]})
    return CycleResult(False,attempts,events,None)
