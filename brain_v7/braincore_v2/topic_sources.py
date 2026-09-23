"""Topic sources for the background factory."""
from __future__ import annotations
import json, os
from typing import Any, Sequence

class EnvTopicResearcher:
    def discover(self, *, audience: str, limit: int = 10) -> Sequence[dict[str, Any]]:
        raw=os.getenv("FACTORY_TOPICS_JSON","[]")
        try: items=json.loads(raw)
        except Exception: items=[]
        if not isinstance(items,list): items=[]
        return items[:limit]
