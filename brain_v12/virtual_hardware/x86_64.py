from __future__ import annotations
from dataclasses import dataclass, field

MASK64 = (1 << 64) - 1

@dataclass
class X86_64CPU:
    """Small deterministic x86-64 interpreter foundation.

    This is intentionally not advertised as a complete x86-64 CPU. It implements
    a testable subset sufficient for the Brain boot/compatibility layer:
    NOP, HLT, MOV r64,imm64, ADD/SUB r64,r64, XOR r64,r64, CMP r64,r64,
    JMP rel8, JZ rel8, and OUT as a Brain diagnostic pseudo-device.
    """
    registers: dict[str, int] = field(default_factory=lambda: {
        r: 0 for r in ("RAX","RBX","RCX","RDX","RSI","RDI","RSP","RBP",
                       "R8","R9","R10","R11","R12","R13","R14","R15","RIP")
    })
    zero_flag: bool = False
    halted: bool = False
    cycles: int = 0
    output: list[int] = field(default_factory=list)

    def reset(self):
        for r in self.registers:
            self.registers[r] = 0
        self.zero_flag = False
        self.halted = False
        self.cycles = 0
        self.output = []

    def _u64(self, value): return int(value) & MASK64

    def step(self, program: list[tuple], max_program_bytes: int = 1 << 20) -> dict:
        if self.halted:
            return {"ok": True, "halted": True, "rip": self.registers["RIP"]}
        rip = self.registers["RIP"]
        if rip < 0 or rip >= len(program) or rip >= max_program_bytes:
            raise RuntimeError("X86_RIP_OUT_OF_RANGE")
        ins = tuple(program[rip])
        op = ins[0]
        next_rip = rip + 1
        if op == "NOP":
            pass
        elif op == "HLT":
            self.halted = True
        elif op == "MOVI":
            reg, value = str(ins[1]).upper(), int(ins[2])
            if reg not in self.registers: raise RuntimeError("X86_BAD_REGISTER")
            self.registers[reg] = self._u64(value)
        elif op in ("ADD","SUB","XOR","CMP"):
            a, b = str(ins[1]).upper(), str(ins[2]).upper()
            if a not in self.registers or b not in self.registers: raise RuntimeError("X86_BAD_REGISTER")
            av, bv = self.registers[a], self.registers[b]
            if op == "ADD": self.registers[a] = self._u64(av + bv)
            elif op == "SUB": self.registers[a] = self._u64(av - bv)
            elif op == "XOR": self.registers[a] = self._u64(av ^ bv)
            self.zero_flag = ((av - bv) & MASK64) == 0 if op == "CMP" else self.registers[a] == 0
        elif op == "JMP":
            next_rip = rip + int(ins[1])
        elif op == "JZ":
            if self.zero_flag: next_rip = rip + int(ins[1])
        elif op == "OUT":
            reg = str(ins[1]).upper()
            if reg not in self.registers: raise RuntimeError("X86_BAD_REGISTER")
            self.output.append(self.registers[reg])
        else:
            raise RuntimeError(f"X86_UNSUPPORTED_OPCODE:{op}")
        self.registers["RIP"] = next_rip
        self.cycles += 1
        return {"ok": True, "opcode": op, "rip": rip, "next_rip": next_rip, "cycles": self.cycles}

    def run(self, program: list[tuple], max_cycles: int = 10000) -> dict:
        trace=[]
        while not self.halted and self.cycles < max_cycles:
            trace.append(self.step(program))
        if not self.halted:
            raise RuntimeError("X86_CYCLE_LIMIT")
        return {"ok": True, "halted": True, "cycles": self.cycles,
                "registers": dict(self.registers), "output": list(self.output), "trace": trace}
