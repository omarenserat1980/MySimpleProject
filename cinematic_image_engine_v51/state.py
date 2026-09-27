from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from .models import ProjectState

class StateManager:
    def __init__(self, project_dir: str):
        self.root = Path(project_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "project_state.json"

    def load(self, project_id: str) -> ProjectState:
        if not self.path.exists():
            return ProjectState(project_id=project_id)
        data=json.loads(self.path.read_text(encoding="utf-8"))
        return ProjectState(**data)

    def save(self, state: ProjectState):
        fd,tmp=tempfile.mkstemp(prefix=".state-", dir=self.root)
        os.close(fd)
        Path(tmp).write_text(json.dumps(state.to_dict(),ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,self.path)

    def verified(self, state, shot_id):
        s=state.shots.get(shot_id,{})
        return s.get("status")=="VERIFIED" and bool(s.get("master_file"))

    def first_unverified(self, state, ordered_ids):
        for sid in ordered_ids:
            if not self.verified(state,sid):
                return sid
        return None
