from __future__ import annotations

from dataclasses import dataclass, field

# Reference profiles are model inputs only; none enables native machine-code execution.
CPU_PROFILES = {
    "brainvm-baseline": {
        "vendor": "Electronic Brain", "model": "Synthetic BrainVM baseline",
        "architecture": "BrainVM-1 tuple ISA", "clock_hz": 1_000_000_000,
        "l1_bytes": 4096, "l2_bytes": 0, "l3_bytes": 0,
        "native_isa_supported": False,
    },
    "intel-core-i7-12700k-reference": {
        "vendor": "Intel", "model": "Core i7-12700K reference profile",
        "architecture": "x86-64 reference; BrainVM tuple ISA remains active",
        "reference_url": "https://www.intel.com/content/www/us/en/products/sku/134599/intel-core-i712700k-processor-25m-cache-up-to-5-00-ghz/specifications.html",
        "clock_hz": 3_600_000_000, "l1_bytes": 81920, "l2_bytes": 1_280_000,
        "l3_bytes": 26_214_400, "native_isa_supported": False,
    },
    "amd-epyc-9654-reference": {
        "vendor": "AMD", "model": "EPYC 9654 reference profile",
        "architecture": "x86-64 reference; BrainVM tuple ISA remains active",
        "reference_url": "https://www.amd.com/en/products/cpu/amd-epyc-9654",
        "clock_hz": 2_400_000_000, "l1_bytes": 65536, "l2_bytes": 1_048_576,
        "l3_bytes": 402_653_184, "native_isa_supported": False,
    },
}

def cpu_profile_metadata(name: str) -> dict:
    if name not in CPU_PROFILES:
        raise ValueError(f"CPU_PROFILE_UNSUPPORTED:{name}")
    return {**CPU_PROFILES[name], "name": name,
            "status": "REFERENCE_PROFILE_NOT_NATIVE_ISA_EMULATION",
            "timing_is_estimated": True, "cycle_accurate": False,
            "pipeline_modeled": False, "privilege_modes_modeled": False,
            "interrupt_delivery_modeled": False}

@dataclass
class VirtualCPU:
    """Deterministic BrainVM-1 tuple interpreter, not an x86/ARM machine-code emulator.

    Supported tuple ops: MOVI, ADD, SUB, LOAD, STORE, JMP, JZ, OUT, HALT.
    Timing and cache counters are transparent estimates, not hardware measurements.
    """
    registers: list[int] = field(default_factory=lambda: [0] * 8)
    pc: int = 0
    zero: bool = False
    halted: bool = False
    cycles: int = 0
    output: list[int] = field(default_factory=list)
    profile_name: str = "brainvm-baseline"
    negative: bool = False
    carry: bool = False
    overflow: bool = False
    cache_stats: dict = field(default_factory=dict)
    _seen_cache_lines: set[int] = field(default_factory=set, repr=False)

    def __post_init__(self) -> None:
        cpu_profile_metadata(self.profile_name)
        if not self.cache_stats:
            self.cache_stats = {"l1_hits": 0, "l1_misses": 0, "l2_hits": 0, "l2_misses": 0, "l3_hits": 0, "l3_misses": 0}

    def select_profile(self, name: str) -> dict:
        metadata = cpu_profile_metadata(name)
        self.profile_name = name
        self._seen_cache_lines.clear()
        self.cache_stats = {"l1_hits": 0, "l1_misses": 0, "l2_hits": 0, "l2_misses": 0, "l3_hits": 0, "l3_misses": 0}
        return metadata

    def fidelity_metadata(self) -> dict:
        return cpu_profile_metadata(self.profile_name)

    def reset(self) -> None:
        self.registers = [0] * 8
        self.pc = 0
        self.zero = self.negative = self.carry = self.overflow = False
        self.halted = False
        self.cycles = 0
        self.output = []
        self._seen_cache_lines.clear()
        self.cache_stats = {"l1_hits": 0, "l1_misses": 0, "l2_hits": 0, "l2_misses": 0, "l3_hits": 0, "l3_misses": 0}

    def _register(self, index) -> int:
        index = int(index)
        if not 0 <= index < len(self.registers):
            raise IndexError("CPU_REGISTER_OUT_OF_RANGE")
        return index

    def _memory_access(self, address: int) -> None:
        line = int(address) // 64
        # Functional presence estimate only; no replacement, associativity, coherence, or TLB.
        if line in self._seen_cache_lines:
            self.cache_stats["l1_hits"] += 1
        else:
            self.cache_stats["l1_misses"] += 1
            self._seen_cache_lines.add(line)

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
            r, value = self._register(ins[1]), int(ins[2])
            self.registers[r] = value
            self.zero, self.negative = value == 0, value < 0
            self.carry = self.overflow = False
            self.pc += 1
        elif op in ("ADD", "SUB"):
            a, b = self._register(ins[1]), self._register(ins[2])
            left, right = self.registers[a], self.registers[b]
            result = left + right if op == "ADD" else left - right
            self.registers[a] = result
            self.zero, self.negative = result == 0, result < 0
            self.carry = (result < 0 or result > 0xFFFFFFFFFFFFFFFF) if op == "ADD" else left < right
            self.overflow = ((left >= 0 and right >= 0 and result < 0) or (left < 0 and right < 0 and result >= 0)) if op == "ADD" else ((left >= 0 and right < 0 and result < 0) or (left < 0 and right >= 0 and result >= 0))
            self.pc += 1
        elif op == "LOAD":
            r, addr = self._register(ins[1]), int(ins[2])
            self.registers[r] = ram.read(addr)
            self._memory_access(addr)
            self.zero, self.negative = self.registers[r] == 0, self.registers[r] < 0
            self.pc += 1
        elif op == "STORE":
            r, addr = self._register(ins[1]), int(ins[2])
            ram.write(addr, self.registers[r])
            self._memory_access(addr)
            self.pc += 1
        elif op == "JMP":
            self.pc = int(ins[1])
        elif op == "JZ":
            self.pc = int(ins[1]) if self.zero else self.pc + 1
        elif op == "OUT":
            self.output.append(self.registers[self._register(ins[1])])
            self.pc += 1
        elif op == "HALT":
            self.halted = True
            self.pc += 1
        else:
            self.halted = True
            raise RuntimeError(f"CPU_ILLEGAL_OPCODE:{op}")
        self.cycles += 1
        return {"ok": True, "pc_before": old_pc, "pc_after": self.pc, "opcode": op, "cycles": self.cycles}

    def run(self, program, ram, max_cycles: int = 10000) -> dict:
        trace = []
        while not self.halted and self.cycles < max_cycles:
            trace.append(self.step(program, ram))
        if not self.halted:
            raise RuntimeError("CPU_CYCLE_LIMIT")
        profile = cpu_profile_metadata(self.profile_name)
        memory_ops = self.cache_stats["l1_hits"] + self.cache_stats["l1_misses"]
        estimated_cycles = self.cycles + self.cache_stats["l1_misses"] * 10
        return {"ok": True, "halted": True, "cycles": self.cycles,
                "estimated_cycles_this_run": estimated_cycles,
                "memory_accesses": memory_ops, "cache_stats": dict(self.cache_stats),
                "flags": {"zero": self.zero, "negative": self.negative, "carry": self.carry, "overflow": self.overflow},
                "profile": profile, "registers": list(self.registers),
                "output": list(self.output), "trace": trace}
