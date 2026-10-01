from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class VirtualCPU:
    """Small deterministic 8-register CPU for the Brain virtual machine.

    Instruction format is tuples: (OP, arg1, arg2).
    Supported ops: MOVI, ADD, SUB, LOAD, STORE, JMP, JZ, OUT, HALT.
    """
    registers: list[int] = field(default_factory=lambda: [0] * 8)
    pc: int = 0
    zero: bool = False
    halted: bool = False
    cycles: int = 0
    output: list[int] = field(default_factory=list)

    def reset(self) -> None:
        self.registers = [0] * 8
        self.pc = 0
        self.zero = False
        self.halted = False
        self.cycles = 0
        self.output = []

    def step(self, program, ram) -> dict:
        if self.halted:
            return {"ok": True, "halted": True, "pc": self.pc}
        if self.pc < 0 or self.pc >= len(program):
            self.halted = True
            raise RuntimeError("CPU_PC_OUT_OF_RANGE")
        ins = tuple(program[self.pc])
        op = ins[0]
        old_pc = self.pc
        if op == "MOVI":
            r, value = int(ins[1]), int(ins[2]); self.registers[r] = int(value); self.pc += 1
        elif op == "ADD":
            a,b = int(ins[1]),int(ins[2]); self.registers[a] += self.registers[b]; self.zero = self.registers[a] == 0; self.pc += 1
        elif op == "SUB":
            a,b = int(ins[1]),int(ins[2]); self.registers[a] -= self.registers[b]; self.zero = self.registers[a] == 0; self.pc += 1
        elif op == "LOAD":
            r,addr = int(ins[1]),int(ins[2]); self.registers[r] = ram.read(addr); self.zero = self.registers[r] == 0; self.pc += 1
        elif op == "STORE":
            r,addr = int(ins[1]),int(ins[2]); ram.write(addr,self.registers[r]); self.pc += 1
        elif op == "JMP":
            self.pc = int(ins[1])
        elif op == "JZ":
            self.pc = int(ins[1]) if self.zero else self.pc + 1
        elif op == "OUT":
            self.output.append(self.registers[int(ins[1])]); self.pc += 1
        elif op == "HALT":
            self.halted = True; self.pc += 1
        else:
            self.halted = True
            raise RuntimeError(f"CPU_ILLEGAL_OPCODE:{op}")
        self.cycles += 1
        return {"ok": True, "pc_before": old_pc, "pc_after": self.pc, "opcode": op, "cycles": self.cycles}

    def run(self, program, ram, max_cycles: int = 10000) -> dict:
        trace=[]
        while not self.halted and self.cycles < max_cycles:
            trace.append(self.step(program,ram))
        if not self.halted:
            raise RuntimeError("CPU_CYCLE_LIMIT")
        return {"ok": True, "halted": True, "cycles": self.cycles, "registers": list(self.registers), "output": list(self.output), "trace": trace}
