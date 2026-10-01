from __future__ import annotations

class VirtualRAM:
    def __init__(self, size: int = 65536):
        if size <= 0: raise ValueError("RAM_SIZE_MUST_BE_POSITIVE")
        self.size=size
        self._data=[0]*size

    def _check(self,address:int):
        if not 0 <= address < self.size: raise IndexError("RAM_ADDRESS_OUT_OF_RANGE")

    def read(self,address:int)->int:
        self._check(address); return self._data[address]

    def write(self,address:int,value:int)->None:
        self._check(address); self._data[address]=int(value)

    def snapshot(self)->dict:
        return {"size":self.size,"nonzero":{str(i):v for i,v in enumerate(self._data) if v != 0}}

    def restore(self,snapshot:dict)->None:
        if int(snapshot.get("size",self.size)) != self.size: raise ValueError("RAM_SIZE_MISMATCH")
        self._data=[0]*self.size
        for k,v in (snapshot.get("nonzero") or {}).items(): self.write(int(k),int(v))
