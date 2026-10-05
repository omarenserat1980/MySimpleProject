from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .permissions import ActionRisk


class AuthorityLevel(str, Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    SUPERVISOR = "SUPERVISOR"


@dataclass(frozen=True)
class AuthorityPolicy:
    """Least-authority policy: higher-risk actions require higher authority."""

    minimum: AuthorityLevel
    irreversible_requires_explicit_approval: bool = True


_LEVEL = {
    AuthorityLevel.SYSTEM: 3,
    AuthorityLevel.USER: 2,
    AuthorityLevel.SUPERVISOR: 1,
}

_REQUIRED = {
    ActionRisk.READ: AuthorityLevel.SUPERVISOR,
    ActionRisk.WRITE: AuthorityLevel.SUPERVISOR,
    ActionRisk.IRREVERSIBLE: AuthorityLevel.USER,
}


class AuthorityGate:
    def __init__(self, policies: dict[str, AuthorityPolicy] | None = None) -> None:
        self._policies = dict(policies or {})

    def evaluate(
        self,
        action: str,
        risk: ActionRisk,
        actor: AuthorityLevel,
        *,
        explicit_approval: bool = False,
    ) -> tuple[bool, str]:
        if not action:
            return False, "action is required"
        policy = self._policies.get(action)
        if policy is None:
            return False, "action has no authority policy"
        if _LEVEL[actor] < _LEVEL[policy.minimum]:
            return False, "actor authority is below policy minimum"
        if risk is ActionRisk.IRREVERSIBLE and not explicit_approval:
            return False, "irreversible action requires explicit approval"
        if risk is ActionRisk.IRREVERSIBLE and policy.minimum is AuthorityLevel.SUPERVISOR:
            return False, "irreversible action cannot be delegated below explicit user authority"
        return True, "authority granted within policy"


__all__ = ["AuthorityGate", "AuthorityLevel", "AuthorityPolicy"]
