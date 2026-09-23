"""Emergency stop for financial side effects."""
from __future__ import annotations
class CircuitBreaker:
    def __init__(self,enabled:bool=True,max_failures:int=3):
        self.enabled=enabled; self.max_failures=max_failures; self.failures=0
    def record_failure(self): self.failures+=1
    def can_submit(self)->bool: return self.enabled and self.failures<self.max_failures
    def trip(self): self.enabled=False
    def reset(self): self.failures=0; self.enabled=True
