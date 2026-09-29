from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class ApiResponse:
    ok: bool
    data: Any = None
    error: str | None = None

    def json(self) -> dict:
        return asdict(self)
