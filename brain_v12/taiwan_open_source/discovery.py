"""Discovery manifest generator for Taiwan open-source candidates."""
from __future__ import annotations
import json
from .catalog import catalog

def build_manifest() -> dict:
    return {
        "schema": "brain-taiwan-open-source/v1",
        "policy": "discover -> verify license -> security/dependency review -> sandbox -> gate -> integrate",
        "projects": catalog(),
    }

if __name__ == "__main__":
    print(json.dumps(build_manifest(), ensure_ascii=False, indent=2))
