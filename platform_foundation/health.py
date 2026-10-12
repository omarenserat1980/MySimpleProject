from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HealthReport:
    status: str
    checks: dict[str, Any]

    @property
    def passed(self) -> bool:
        return self.status == "PASS" and all(bool(v) for v in self.checks.values())
