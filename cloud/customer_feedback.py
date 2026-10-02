"""Evidence-first customer feedback and product-improvement loop."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import hashlib, json, os, tempfile, uuid

def now_iso(): return datetime.now(timezone.utc).isoformat()

class FeedbackState(str, Enum):
    RECEIVED="RECEIVED"; TRIAGED="TRIAGED"; ASSIGNED="ASSIGNED"; IN_PROGRESS="IN_PROGRESS"
    RESPONDED="RESPONDED"; RESOLVED="RESOLVED"; CLOSED="CLOSED"
    LEGAL_HOLD="LEGAL_HOLD"; SPAM="SPAM"; DUPLICATE="DUPLICATE"

_ALLOWED={
 FeedbackState.RECEIVED:{FeedbackState.TRIAGED,FeedbackState.SPAM,FeedbackState.DUPLICATE,FeedbackState.LEGAL_HOLD},
 FeedbackState.TRIAGED:{FeedbackState.ASSIGNED,FeedbackState.IN_PROGRESS,FeedbackState.SPAM,FeedbackState.DUPLICATE,FeedbackState.LEGAL_HOLD},
 FeedbackState.ASSIGNED:{FeedbackState.IN_PROGRESS,FeedbackState.LEGAL_HOLD},
 FeedbackState.IN_PROGRESS:{FeedbackState.RESPONDED,FeedbackState.RESOLVED,FeedbackState.LEGAL_HOLD},
 FeedbackState.RESPONDED:{FeedbackState.RESOLVED,FeedbackState.CLOSED,FeedbackState.LEGAL_HOLD},
 FeedbackState.RESOLVED:{FeedbackState.CLOSED,FeedbackState.LEGAL_HOLD},
 FeedbackState.CLOSED:{FeedbackState.LEGAL_HOLD},
 FeedbackState.LEGAL_HOLD:{FeedbackState.CLOSED},
 FeedbackState.SPAM:set(), FeedbackState.DUPLICATE:set(),
}

@dataclass
class Feedback:
    customer_id: str | None
    rating: int | None
    category: str
    body: str
    consent_to_contact: bool=False
    marketing_consent: bool=False
    request_id: str | None=None
    case_id: str | None=None
    feedback_id: str=field(default_factory=lambda:str(uuid.uuid4()))
    state: FeedbackState=FeedbackState.RECEIVED
    created_at: str=field(default_factory=now_iso)
    updated_at: str=field(default_factory=now_iso)
    assigned_to: str | None=None
    resolution: str | None=None
    evidence_ref: str | None=None
    content_hash: str=""
    events: list[dict]=field(default_factory=list)

    def __post_init__(self):
        if self.rating is not None and not 1 <= int(self.rating) <= 5:
            raise ValueError("rating must be between 1 and 5")
        if not self.category.strip(): raise ValueError("category is required")
        if not self.body.strip(): raise ValueError("body is required")
        self.content_hash=hashlib.sha256(self.body.encode("utf-8")).hexdigest()
        if not self.events:
            self.events=[{"event":"CREATED","at":self.created_at,"state":self.state.value}]

    def transition(self,new_state:FeedbackState,actor:str,evidence_ref:str|None=None,reason:str=""):
        if new_state not in _ALLOWED[self.state]: raise ValueError(f"invalid transition {self.state.value}->{new_state.value}")
        if new_state in {FeedbackState.RESPONDED,FeedbackState.RESOLVED,FeedbackState.CLOSED} and not evidence_ref:
            raise ValueError("response/resolution/closure requires evidence_ref")
        old=self.state.value; self.state=new_state; self.updated_at=now_iso()
        if evidence_ref: self.evidence_ref=evidence_ref
        self.events.append({"event":"STATE_CHANGED","from":old,"to":new_state.value,"actor":actor,"reason":reason,"at":self.updated_at,"evidence_ref":evidence_ref})

    def assign(self,owner:str):
        if not owner.strip(): raise ValueError("owner is required")
        self.assigned_to=owner.strip()
        if self.state==FeedbackState.TRIAGED: self.transition(FeedbackState.ASSIGNED,owner)
        self.events.append({"event":"ASSIGNED","owner":owner.strip(),"at":now_iso()})

class FeedbackStore:
    def __init__(self,root:Path|None=None):
        self.root=Path(root or os.getenv("BRAIN_STATE_DIR",".brain_state"))/"customer_feedback"
        self.root.mkdir(parents=True,exist_ok=True)
    def _path(self,fid): return self.root/(fid+".json")
    def save(self,f:Feedback):
        p=self._path(f.feedback_id); fd,tmp=tempfile.mkstemp(dir=self.root,prefix=".tmp-")
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:
                json.dump(asdict(f),h,ensure_ascii=False,indent=2); h.flush(); os.fsync(h.fileno())
            os.replace(tmp,p)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    def create(self,**kwargs):
        f=Feedback(**kwargs); self.save(f); return f
    def get(self,fid):
        p=self._path(fid)
        if not p.exists(): raise FileNotFoundError(fid)
        d=json.loads(p.read_text(encoding="utf-8")); d["state"]=FeedbackState(d["state"]); return Feedback(**d)
    def list(self,limit=100):
        out=[]
        for p in sorted(self.root.glob("*.json"),key=lambda x:x.stat().st_mtime,reverse=True)[:max(1,min(limit,500))]:
            try: out.append(self.get(p.stem))
            except Exception: continue
        return out
