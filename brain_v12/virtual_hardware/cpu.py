from __future__ import annotations
from dataclasses import dataclass, field

# Hardware reference metadata only: these profiles do not enable native x86-64/ARM execution.
CPU_PROFILES = {
 "brainvm-baseline": {"vendor":"Electronic Brain","model":"Synthetic BrainVM baseline","architecture":"BrainVM-1 tuple ISA","reference_url":"https://github.com/omarenserat1980/MySimpleProject","isa_spec_url":"https://github.com/omarenserat1980/MySimpleProject","clock_hz":1_000_000_000,"l1_bytes":16384,"l2_bytes":262144,"l3_bytes":0,"native_isa_supported":False},
 "intel-core-i7-12700k-reference": {"vendor":"Intel","model":"Core i7-12700K (Alder Lake-S; P/E cores)","architecture":"x86-64 reference; BrainVM ISA remains active","reference_url":"https://www.intel.com/content/www/us/en/products/sku/134599/intel-core-i712700k-processor-25m-cache-up-to-5-00-ghz/specifications.html","isa_spec_url":"https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html","clock_hz":3_600_000_000,"l1_bytes":81920,"l2_bytes":1280000,"l3_bytes":26214400,"native_isa_supported":False},
 "amd-epyc-9654-reference": {"vendor":"AMD","model":"EPYC 9654 (Zen 4, Genoa)","architecture":"x86-64 reference; BrainVM ISA remains active","reference_url":"https://www.amd.com/en/products/cpu/amd-epyc-9654","isa_spec_url":"https://www.amd.com/en/search/documentation/hub.html","clock_hz":2_400_000_000,"l1_bytes":65536,"l2_bytes":1048576,"l3_bytes":402653184,"native_isa_supported":False}
}

def cpu_profile_metadata(name):
    if name not in CPU_PROFILES: raise ValueError(f"CPU_PROFILE_UNSUPPORTED:{name}")
    return {**CPU_PROFILES[name], "name":name,"status":"REFERENCE_PROFILE_NOT_NATIVE_ISA_EMULATION",
            "timing_is_estimated":True,"cycle_accurate":False,"pipeline_model":"not modeled",
            "cache_model":"simple deterministic line-presence approximation"}

@dataclass
class VirtualCPU:
    """Backwards-compatible BrainVM-1 tuple interpreter with estimated memory costs.

    Supported tuple operations: MOVI, ADD, SUB, LOAD, STORE, JMP, JZ, OUT, HALT.
    This is not an x86-64/ARM byte decoder, cycle-accurate pipeline, or privileged CPU.
    """
    registers: list[int] = field(default_factory=lambda: [0] * 8)
    pc: int = 0
    zero: bool = False
    halted: bool = False
    cycles: int = 0
    output: list[int] = field(default_factory=list)
    profile_name: str = "brainvm-baseline"
    flags: dict[str, bool] = field(default_factory=lambda: {"zero":False,"negative":False,"carry":False,"overflow":False})
    estimated_cycles: int = 0
    instruction_count: int = 0
    cache_stats: dict[str, int] = field(default_factory=lambda: {"l1_hits":0,"l2_hits":0,"l3_hits":0,"memory_accesses":0})
    _cache_lines: dict[str, set[int]] = field(default_factory=lambda: {"l1":set(),"l2":set(),"l3":set()})

    def __post_init__(self):
        cpu_profile_metadata(self.profile_name)

    def select_profile(self, name):
        cpu_profile_metadata(name); self.profile_name=name
        self._cache_lines={"l1":set(),"l2":set(),"l3":set()}
        self.cache_stats={"l1_hits":0,"l2_hits":0,"l3_hits":0,"memory_accesses":0}
        return self.fidelity_metadata()

    def fidelity_metadata(self):
        return {**cpu_profile_metadata(self.profile_name),"functional_isa":"BrainVM-1 tuple ISA",
                "supported_opcodes":["MOVI","ADD","SUB","LOAD","STORE","JMP","JZ","OUT","HALT"],
                "register_count":8,"register_width_bits":"unbounded Python integers, not hardware width",
                "flags":["zero","negative","carry","overflow"],"privilege_modes":"not modeled",
                "interrupt_delivery":"not modeled; VirtualBus queue remains separate",
                "native_instruction_decoding":False,"pipeline":"not modeled",
                "unsupported_native_isa":["x86-64","AArch64/ARM"]}

    def reset(self) -> None:
        self.registers=[0]*8; self.pc=0; self.zero=False; self.halted=False
        self.cycles=0; self.output=[]; self.flags={"zero":False,"negative":False,"carry":False,"overflow":False}
        self.estimated_cycles=0; self.instruction_count=0
        self.cache_stats={"l1_hits":0,"l2_hits":0,"l3_hits":0,"memory_accesses":0}
        self._cache_lines={"l1":set(),"l2":set(),"l3":set()}

    def _cache_cost(self,address):
        p=CPU_PROFILES[self.profile_name]; line=int(address)//64
        if line in self._cache_lines["l1"]: self.cache_stats["l1_hits"]+=1; return 1
        if line in self._cache_lines["l2"]: self.cache_stats["l2_hits"]+=1; self._cache_lines["l1"].add(line); return 4
        if p["l3_bytes"] and line in self._cache_lines["l3"]: self.cache_stats["l3_hits"]+=1; self._cache_lines["l2"].add(line); self._cache_lines["l1"].add(line); return 12
        self.cache_stats["memory_accesses"]+=1; self._cache_lines["l1"].add(line); self._cache_lines["l2"].add(line)
        if p["l3_bytes"]: self._cache_lines["l3"].add(line)
        return 80

    def _set_flags(self,value,carry=False,overflow=False):
        self.zero=value==0; self.flags={"zero":self.zero,"negative":value<0,"carry":carry,"overflow":overflow}

    def step(self, program, ram) -> dict:
        if self.halted: return {"ok":True,"halted":True,"pc":self.pc}
        if self.pc<0 or self.pc>=len(program):
            self.halted=True; raise RuntimeError("CPU_PC_OUT_OF_RANGE")
        ins=tuple(program[self.pc])
        if not ins: raise RuntimeError("CPU_MALFORMED_INSTRUCTION")
        op=str(ins[0]).upper(); old_pc=self.pc; cost=1
        if op=="MOVI":
            r,value=int(ins[1]),int(ins[2])
            if not 0<=r<8: raise RuntimeError("CPU_BAD_REGISTER")
            self.registers[r]=value; self._set_flags(value); self.pc+=1
        elif op in ("ADD","SUB"):
            a,b=int(ins[1]),int(ins[2])
            if not (0<=a<8 and 0<=b<8): raise RuntimeError("CPU_BAD_REGISTER")
            lhs,rhs=self.registers[a],self.registers[b]; value=lhs+rhs if op=="ADD" else lhs-rhs
            self.registers[a]=value; self._set_flags(value,carry=(op=="ADD" and value<lhs)); self.pc+=1
        elif op=="LOAD":
            r,addr=int(ins[1]),int(ins[2])
            if not 0<=r<8: raise RuntimeError("CPU_BAD_REGISTER")
            self.registers[r]=ram.read(addr); self._set_flags(self.registers[r]); cost+=self._cache_cost(addr); self.pc+=1
        elif op=="STORE":
            r,addr=int(ins[1]),int(ins[2])
            if not 0<=r<8: raise RuntimeError("CPU_BAD_REGISTER")
            ram.write(addr,self.registers[r]); cost+=self._cache_cost(addr); self.pc+=1
        elif op=="JMP": self.pc=int(ins[1])
        elif op=="JZ": self.pc=int(ins[1]) if self.zero else self.pc+1
        elif op=="OUT":
            r=int(ins[1])
            if not 0<=r<8: raise RuntimeError("CPU_BAD_REGISTER")
            self.output.append(self.registers[r]); self.pc+=1
        elif op=="HALT": self.halted=True; self.pc+=1
        else:
            self.halted=True; raise RuntimeError(f"CPU_ILLEGAL_OPCODE:{op}")
        self.cycles+=1; self.instruction_count+=1; self.estimated_cycles+=cost
        return {"ok":True,"pc_before":old_pc,"pc_after":self.pc,"opcode":op,"cycles":self.cycles,"estimated_cost_cycles":cost}

    def run(self, program, ram, max_cycles: int = 10000) -> dict:
        trace=[]; before=self.instruction_count; est_before=self.estimated_cycles
        while not self.halted and self.cycles<max_cycles: trace.append(self.step(program,ram))
        if not self.halted: raise RuntimeError("CPU_CYCLE_LIMIT")
        return {"ok":True,"halted":True,"cycles":self.cycles,"instructions_this_run":self.instruction_count-before,
                "estimated_cycles_this_run":self.estimated_cycles-est_before,"profile":self.profile_name,
                "fidelity":self.fidelity_metadata(),"cache_stats":dict(self.cache_stats),
                "registers":list(self.registers),"flags":dict(self.flags),"output":list(self.output),"trace":trace}
