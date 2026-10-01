from __future__ import annotations

class VirtualBus:
    """Deterministic motherboard bus/device registry."""
    def __init__(self):
        self.devices={}
        self.interrupts=[]

    def attach(self,name,device):
        if name in self.devices: raise ValueError(f"DEVICE_ALREADY_ATTACHED:{name}")
        self.devices[name]=device
        return {"ok":True,"device":name}

    def interrupt(self,source,payload=None):
        event={"source":source,"payload":payload or {}}
        self.interrupts.append(event)
        return event

    def device_names(self): return sorted(self.devices)
