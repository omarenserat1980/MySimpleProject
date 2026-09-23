"""Provider-neutral payout adapter contract.

Concrete providers implement this interface outside the core. Secrets belong
in the provider's secret manager/environment, never in source or chat.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class TransferResult:
    status:str
    provider_reference:str|None=None
    amount_jod:float|None=None
    error_code:str|None=None

class PaymentProvider(Protocol):
    def submit(self, amount_jod:float, destination_ref:str, idempotency_key:str) -> TransferResult: ...
    def status(self, provider_reference:str) -> TransferResult: ...

class MockPaymentProvider:
    """Test-only provider. It never moves real money."""
    def submit(self, amount_jod:float, destination_ref:str, idempotency_key:str)->TransferResult:
        return TransferResult("SIMULATED",f"SIM-{idempotency_key[:12]}",amount_jod)
    def status(self, provider_reference:str)->TransferResult:
        return TransferResult("SIMULATED",provider_reference)
