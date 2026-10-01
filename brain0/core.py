"""Deterministic BRAIN-0/1 virtual machine."""
from dataclasses import dataclass, field
NOP=0x00; LOAD=0x01; STORE=0x02; ADD=0x03; SUB=0x04
CMP=0x05; JUMP=0x06; HALT=0x07; READ=0x08; WRITE=0x09
VERIFY=0x0A; TASK=0x0B

@dataclass
class BrainVM:
    memory_size:int=256
    registers:list[int]=field(default_factory=lambda:[0]*8)
    memory:bytearray=field(init=False)
    pc:int=0
    halted:bool=False
    verified:bool=False
    steps:int=0
    evidence:list[dict]=field(default_factory=list)

    def __post_init__(self):
        self.memory=bytearray(self.memory_size)

    def load(self, program:bytes)->None:
        if len(program)>self.memory_size: raise ValueError("PROGRAM_TOO_LARGE")
        self.memory[:len(program)]=program
        self.pc=0; self.halted=False; self.verified=False; self.steps=0; self.evidence=[]

    def _reg(self,n:int)->None:
        if not 0<=n<len(self.registers): raise ValueError("INVALID_REGISTER")

    def step(self)->None:
        if self.halted: return
        op,a,b,c=self.memory[self.pc:self.pc+4]
        next_pc=self.pc+4
        if op==NOP: pass
        elif op==LOAD:
            self._reg(a); self.registers[a]=b | (c<<8)
        elif op==STORE:
            self._reg(a); addr=b | (c<<8); self.memory[addr]=self.registers[a]&255
        elif op==ADD:
            self._reg(a); self._reg(b); self.registers[a]=(self.registers[a]+self.registers[b])&0xFFFF
        elif op==SUB:
            self._reg(a); self._reg(b); self.registers[a]=(self.registers[a]-self.registers[b])&0xFFFF
        elif op==CMP:
            self._reg(a); self._reg(b); self.registers[0]=1 if self.registers[a]==self.registers[b] else 0
        elif op==JUMP: next_pc=a | (b<<8)
        elif op==HALT: self.halted=True
        elif op==READ:
            self._reg(a); addr=b | (c<<8); self.registers[a]=self.memory[addr]
        elif op==WRITE:
            self._reg(a); addr=b | (c<<8); self.memory[addr]=self.registers[a]&255
        elif op==VERIFY:
            self._reg(a); expected=b | (c<<8); self.verified=self.registers[a]==expected
            self.evidence.append({"type":"VERIFY","register":a,"actual":self.registers[a],"expected":expected,"verified":self.verified})
        elif op==TASK:
            self.evidence.append({"type":"TASK","id":a,"arg":b | (c<<8)})
        else: raise RuntimeError("UNKNOWN_OPCODE:%02X"%op)
        self.pc=next_pc; self.steps+=1

    def run(self,max_steps:int=1000)->dict:
        while not self.halted:
            if self.steps>=max_steps: raise RuntimeError("STEP_LIMIT")
            self.step()
        status="VERIFIED_COMPLETED" if self.verified else "COMPLETED"
        return {"status":status,"pc":self.pc,"steps":self.steps,"registers":self.registers[:],"evidence":self.evidence}

def encode(op,a=0,b=0,c=0): return bytes((op,a,b,c))
