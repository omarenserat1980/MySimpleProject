"""Tamper-evident audit chain for BRAIN-0/1."""
from dataclasses import dataclass, field
import hashlib, json, time

@dataclass
class EvidenceChain:
    entries:list[dict]=field(default_factory=list)
    last_hash:str="0"*64

    def append(self,event,**data):
        payload={"seq":len(self.entries)+1,"ts":time.time(),"event":event,"data":data,"prev_hash":self.last_hash}
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()
        digest=hashlib.sha256(raw).hexdigest()
        payload["hash"]=digest
        self.entries.append(payload)
        self.last_hash=digest
        return payload

    def verify(self):
        previous="0"*64
        for entry in self.entries:
            if entry["prev_hash"]!=previous: return False
            copy=dict(entry); digest=copy.pop("hash")
            raw=json.dumps(copy,sort_keys=True,separators=(",",":"),default=str).encode()
            if hashlib.sha256(raw).hexdigest()!=digest: return False
            previous=digest
        return True
