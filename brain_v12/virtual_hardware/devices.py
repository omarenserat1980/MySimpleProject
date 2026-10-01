from __future__ import annotations
import hashlib

class VirtualStorage:
    def __init__(self,capacity:int=1024*1024):
        self.capacity=capacity; self.files={}
    def write(self,path:str,data:bytes):
        used=sum(len(v) for v in self.files.values())
        old=len(self.files.get(path,b""))
        if used-old+len(data)>self.capacity: raise RuntimeError("VSTORAGE_FULL")
        self.files[path]=bytes(data)
    def read(self,path:str)->bytes:
        if path not in self.files: raise FileNotFoundError(path)
        return self.files[path]
    def manifest(self):
        return {p:{"size":len(v),"sha256":hashlib.sha256(v).hexdigest()} for p,v in sorted(self.files.items())}

class VirtualNIC:
    def __init__(self,mac:str="02:42:42:52:00:01"):
        self.mac=mac; self.rx=[]; self.tx=[]
    def send(self,payload:bytes):
        packet=bytes(payload); self.tx.append(packet); return {"ok":True,"bytes":len(packet)}
    def inject(self,payload:bytes):
        packet=bytes(payload); self.rx.append(packet); return {"ok":True,"bytes":len(packet)}
    def receive(self):
        return self.rx.pop(0) if self.rx else None

class VirtualGPU:
    def __init__(self,width:int=320,height:int=200):
        self.width=width; self.height=height; self.framebuffer=[0]*(width*height)
    def clear(self,value:int=0):
        self.framebuffer=[int(value)]*(self.width*self.height)
    def pixel(self,x:int,y:int,value:int):
        if not (0<=x<self.width and 0<=y<self.height): raise IndexError("GPU_COORDINATES_OUT_OF_RANGE")
        self.framebuffer[y*self.width+x]=int(value)
