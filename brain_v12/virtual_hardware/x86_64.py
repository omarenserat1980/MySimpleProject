from __future__ import annotations
from dataclasses import dataclass, field

from .cpu_profiles import get_cpu_profile

MASK64 = (1 << 64) - 1
SIGN64 = 1 << 63


class X86UnsupportedInstruction(RuntimeError):
    """Structured unsupported-instruction report; not a hardware #UD implementation."""

    def __init__(self, opcode: str, rip: int, profile_id: str):
        self.opcode = opcode
        self.rip = rip
        self.profile_id = profile_id
        super().__init__(f"X86_UNSUPPORTED_OPCODE:{opcode}:RIP={rip}:PROFILE={profile_id}")


@dataclass
class X86_64CPU:
    """Functional symbolic-instruction subset with explicit profile and fidelity metadata.

    The input is a list of symbolic tuples, not encoded x86 instruction bytes. One counter
    increment means one interpreted tuple; it is not a physical CPU cycle estimate.
    """
    registers: dict[str, int] = field(default_factory=lambda: {
        r: 0 for r in ("RAX","RBX","RCX","RDX","RSI","RDI","RSP","RBP",
                       "R8","R9","R10","R11","R12","R13","R14","R15","RIP")
    })
    zero_flag: bool = False
    halted: bool = False
    cycles: int = 0
    output: list[int] = field(default_factory=list)
    profile_id: str = "brain-x86-64-subset-v1"
    flags: dict[str, bool] = field(default_factory=lambda: {
        "CF": False, "PF": False, "AF": False, "ZF": False,
        "SF": False, "OF": False, "IF": True, "DF": False,
    })
    privilege_level: int = 3
    interrupts_enabled: bool = True
    pending_interrupts: list[int] = field(default_factory=list)

    def __post_init__(self):
        get_cpu_profile(self.profile_id)
        if self.privilege_level not in (0, 1, 2, 3):
            raise ValueError("X86_PRIVILEGE_LEVEL_INVALID")

    @property
    def profile(self) -> dict:
        return get_cpu_profile(self.profile_id).describe()

    def unsupported_instruction_report(self, opcode: str | None = None) -> dict:
        return {
            "profile_id": self.profile_id,
            "fidelity": self.profile["fidelity"],
            "opcode": opcode,
            "supported_symbolic_opcodes": ["NOP", "HLT", "MOVI", "ADD", "SUB", "XOR", "CMP", "JMP", "JZ", "OUT"],
            "binary_instruction_decoding": False,
            "unsupported_features": list(self.profile["unsupported_features"]),
        }

    def request_interrupt(self, vector: int) -> dict:
        if not 0 <= int(vector) <= 255:
            raise ValueError("X86_INTERRUPT_VECTOR_OUT_OF_RANGE")
        self.pending_interrupts.append(int(vector))
        return {"ok": True, "queued": True, "vector": int(vector), "delivered": False,
                "note": "Interrupts are recorded only; architectural IDT delivery is unsupported."}

    def reset(self):
        for r in self.registers:
            self.registers[r] = 0
        self.zero_flag = False
        self.halted = False
        self.cycles = 0
        self.output = []
        self.flags = {"CF": False, "PF": False, "AF": False, "ZF": False,
                      "SF": False, "OF": False, "IF": True, "DF": False}
        self.privilege_level = 3
        self.interrupts_enabled = True
        self.pending_interrupts = []

    def _u64(self, value):
        return int(value) & MASK64

    @staticmethod
    def _parity(value: int) -> bool:
        return (value & 0xFF).bit_count() % 2 == 0

    def _set_result_flags(self, result: int, carry: bool = False, overflow: bool = False,
                          auxiliary_carry: bool = False) -> None:
        result &= MASK64
        self.flags["CF"] = bool(carry)
        self.flags["ZF"] = result == 0
        self.flags["SF"] = bool(result & SIGN64)
        self.flags["PF"] = self._parity(result)
        self.flags["OF"] = bool(overflow)
        self.flags["AF"] = bool(auxiliary_carry)
        self.zero_flag = self.flags["ZF"]

    def _register(self, name) -> str:
        reg = str(name).upper()
        if reg not in self.registers or reg == "RIP":
            raise RuntimeError(f"X86_BAD_REGISTER:{reg}")
        return reg

    def step(self, program: list[tuple], max_program_bytes: int = 1 << 20) -> dict:
        if self.halted:
            return {"ok": True, "halted": True, "rip": self.registers["RIP"]}
        rip = self.registers["RIP"]
        if rip < 0 or rip >= len(program) or rip >= max_program_bytes:
            raise RuntimeError("X86_RIP_OUT_OF_RANGE")
        try:
            ins = tuple(program[rip])
        except (TypeError, IndexError) as exc:
            raise RuntimeError(f"X86_INVALID_SYMBOLIC_INSTRUCTION:RIP={rip}") from exc
        if not ins or not isinstance(ins[0], str):
            raise RuntimeError(f"X86_INVALID_SYMBOLIC_INSTRUCTION:RIP={rip}")
        op = ins[0].upper()
        next_rip = rip + 1
        if op == "NOP":
            pass
        elif op == "HLT":
            self.halted = True
        elif op == "MOVI":
            reg, value = self._register(ins[1]), int(ins[2])
            self.registers[reg] = self._u64(value)
        elif op in ("ADD", "SUB", "XOR", "CMP"):
            a, b = self._register(ins[1]), self._register(ins[2])
            av, bv = self.registers[a], self.registers[b]
            if op == "ADD":
                raw = av + bv
                result = self._u64(raw)
                self.registers[a] = result
                self._set_result_flags(result, raw > MASK64,
                    bool((~(av ^ bv) & (av ^ result) & SIGN64) != 0),
                    (av & 0xF) + (bv & 0xF) > 0xF)
            elif op in ("SUB", "CMP"):
                result = self._u64(av - bv)
                if op == "SUB":
                    self.registers[a] = result
                self._set_result_flags(result, av < bv,
                    bool(((av ^ bv) & (av ^ result) & SIGN64) != 0),
                    (av & 0xF) < (bv & 0xF))
            else:
                result = self._u64(av ^ bv)
                self.registers[a] = result
                self._set_result_flags(result, False, False, False)
        elif op == "JMP":
            next_rip = rip + int(ins[1])
        elif op == "JZ":
            if self.flags["ZF"]: next_rip = rip + int(ins[1])
        elif op == "OUT":
            reg = self._register(ins[1])
            self.output.append(self.registers[reg])
        else:
            raise X86UnsupportedInstruction(op, rip, self.profile_id)
        self.registers["RIP"] = next_rip
        self.cycles += 1
        return {"ok": True, "opcode": op, "rip": rip, "next_rip": next_rip,
                "cycles": self.cycles, "counter_semantics": "interpreted_symbolic_instruction"}

    def run(self, program: list[tuple], max_cycles: int = 10000) -> dict:
        trace = []
        while not self.halted and self.cycles < max_cycles:
            trace.append(self.step(program))
        if not self.halted:
            raise RuntimeError("X86_CYCLE_LIMIT")
        return {"ok": True, "halted": True, "cycles": self.cycles,
                "counter_semantics": "interpreted_symbolic_instruction",
                "profile": self.profile, "registers": dict(self.registers),
                "flags": dict(self.flags), "output": list(self.output), "trace": trace}
