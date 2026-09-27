from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

@dataclass
class Shot:
    shot_id: str
    scene_id: str
    purpose: str
    characters: List[str] = field(default_factory=list)
    location: str = ""
    action: str = ""
    camera: str = "medium"
    lens: str = "50mm"
    composition: str = ""
    light: str = ""
    emotion: str = ""
    continuity: Dict[str, Any] = field(default_factory=dict)
    status: str = "UNVERIFIED"
    master_file: str | None = None
    attempts: int = 0
    qc: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProjectState:
    project_id: str
    version: str = "5.1.0"
    status: str = "RUNNING"
    shots: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    continuity: Dict[str, Any] = field(default_factory=dict)
    operations: Dict[str, str] = field(default_factory=dict)
    last_completed_operation: str | None = None
    model_info: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self):
        return asdict(self)
