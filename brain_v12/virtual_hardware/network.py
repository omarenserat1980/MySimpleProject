from __future__ import annotations
from dataclasses import dataclass

@dataclass
class VirtualPacket:
    src:str
    dst:str
    payload:bytes

class VirtualRouter:
    """In-memory packet router; no physical/network access is implied."""
    def __init__(self):
        self.routes={}
        self.delivered=[]
    def register(self,address,nic):
        self.routes[address]=nic
    def send(self,packet:VirtualPacket):
        nic=self.routes.get(packet.dst)
        if nic is None: return {"ok":False,"status":"NO_ROUTE","dst":packet.dst}
        nic.inject(packet.payload)
        self.delivered.append(packet)
        return {"ok":True,"status":"DELIVERED","dst":packet.dst,"bytes":len(packet.payload)}
