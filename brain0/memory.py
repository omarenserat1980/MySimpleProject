"""Persistent-free deterministic memory layer for BRAIN-0/1."""
from dataclasses import dataclass, field
import hashlib, json, time

@dataclass
class Memory:
    values:dict[str,object]=field(default_factory=dict)
    version:int=0

    def put(self,key,value):
        self.values[key]=value
        self.version+=1
        return self.version

    def get(self,key,default=None):
        return self.values.get(key,default)

    def snapshot(self):
        raw=json.dumps(self.values,sort_keys=True,separators=(",",":"),default=str).encode()
        return {"version":self.version,"sha256":hashlib.sha256(raw).hexdigest(),"values":dict(self.values)}
