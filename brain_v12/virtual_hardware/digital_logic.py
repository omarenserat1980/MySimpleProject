"""Foundational digital logic primitives for the BrainVM simulation.

These are deterministic software models. Logical ticks are not a physical clock
frequency, and calculator operations do not represent measured hardware speed.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DigitalClock:
    """A manually advanced logical clock with bounded counter and rollover."""
    width_bits: int = 16
    ticks: int = 0
    enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.width_bits, int) or not 1 <= self.width_bits <= 64:
            raise ValueError("CLOCK_WIDTH_MUST_BE_1_TO_64")
        if not isinstance(self.ticks, int) or not 0 <= self.ticks <= self.max_ticks:
            raise ValueError("CLOCK_TICKS_OUT_OF_RANGE")

    @property
    def max_ticks(self) -> int:
        return (1 << self.width_bits) - 1

    def pulse(self, count: int = 1) -> dict:
        if not isinstance(count, int) or count < 0:
            raise ValueError("CLOCK_PULSE_COUNT_INVALID")
        if self.enabled:
            self.ticks = (self.ticks + count) & self.max_ticks
        return self.status()

    def reset(self) -> dict:
        self.ticks = 0
        return self.status()

    def status(self) -> dict:
        return {
            "component": "DigitalClock",
            "mode": "SIMULATED_LOGICAL_TICKS",
            "width_bits": self.width_bits,
            "ticks": self.ticks,
            "max_ticks": self.max_ticks,
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class CalculatorResult:
    operation: str
    left: int
    right: int
    value: int
    overflow: bool
    width_bits: int
    signed: bool


class MiniCalculator:
    """Integer arithmetic with explicit width and signed/unsigned overflow rules."""
    def __init__(self, width_bits: int = 8, signed: bool = False):
        if not isinstance(width_bits, int) or not 1 <= width_bits <= 64:
            raise ValueError("CALCULATOR_WIDTH_MUST_BE_1_TO_64")
        self.width_bits = width_bits
        self.signed = bool(signed)

    @property
    def minimum(self) -> int:
        return -(1 << (self.width_bits - 1)) if self.signed else 0

    @property
    def maximum(self) -> int:
        return (1 << (self.width_bits - 1)) - 1 if self.signed else (1 << self.width_bits) - 1

    def calculate(self, operation: str, left: int, right: int) -> dict:
        if not isinstance(left, int) or isinstance(left, bool):
            raise TypeError("CALCULATOR_OPERANDS_MUST_BE_INTEGERS")
        if not isinstance(right, int) or isinstance(right, bool):
            raise TypeError("CALCULATOR_OPERANDS_MUST_BE_INTEGERS")
        if not self.minimum <= left <= self.maximum or not self.minimum <= right <= self.maximum:
            raise ValueError("CALCULATOR_OPERAND_OUT_OF_RANGE")
        if operation == "ADD":
            raw = left + right
        elif operation == "SUB":
            raw = left - right
        elif operation == "MUL":
            raw = left * right
        elif operation == "DIV":
            if right == 0:
                raise ZeroDivisionError("CALCULATOR_DIVIDE_BY_ZERO")
            # Truncate toward zero, matching integer hardware-style division.
            raw = abs(left) // abs(right) * (-1 if (left < 0) != (right < 0) else 1)
        else:
            raise ValueError(f"CALCULATOR_UNSUPPORTED_OPERATION:{operation}")
        overflow = not self.minimum <= raw <= self.maximum
        modulus = 1 << self.width_bits
        value = raw % modulus
        if self.signed and value >= (1 << (self.width_bits - 1)):
            value -= modulus
        result = CalculatorResult(operation, left, right, value, overflow,
                                 self.width_bits, self.signed)
        return {
            "ok": True,
            "mode": "SIMULATED_INTEGER_ARITHMETIC",
            "operation": result.operation,
            "left": result.left,
            "right": result.right,
            "value": result.value,
            "raw_value": raw,
            "overflow": result.overflow,
            "width_bits": result.width_bits,
            "signed": result.signed,
        }
