"""Zero-touch controller.

Zero-touch means no human intervention for planning, research normalization,
local artifact creation, validation, packaging, and learning.

External side effects (submitting jobs, sending messages, signing agreements,
charging/transferring money) remain explicitly gated by authorization and
provider confirmation. The controller never bypasses those controls.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ZeroTouchState:
    objective: str
    local_autonomy: bool
    external_submission_authorized: bool
    payment_authorized: bool
    provider_confirmed: bool

    @property
    def fully_autonomous(self) -> bool:
        return self.local_autonomy and (
            self.external_submission_authorized
            and self.payment_authorized
            and self.provider_confirmed
        )


def build_zero_touch_plan(objective: str, *,
                           external_submission_authorized: bool = False,
                           payment_authorized: bool = False,
                           provider_confirmed: bool = False) -> dict:
    state = ZeroTouchState(
        objective=objective.strip(),
        local_autonomy=True,
        external_submission_authorized=external_submission_authorized,
        payment_authorized=payment_authorized,
        provider_confirmed=provider_confirmed,
    )
    return {
        "mode": "ZERO_TOUCH_LOCAL",
        "objective": state.objective,
        "autonomous_steps": [
            "discover",
            "qualify",
            "research",
            "create_artifact",
            "validate",
            "package",
            "learn",
            "replan",
        ],
        "external_side_effects_allowed": state.fully_autonomous,
        "submission_gate": not external_submission_authorized,
        "payment_gate": not payment_authorized,
        "provider_confirmation_gate": not provider_confirmed,
        "fully_autonomous": state.fully_autonomous,
        "safety_rule": "never bypass authorization, credentials, KYC, limits, or provider confirmation",
    }


def can_execute_locally() -> bool:
    return True


def can_submit_externally(*, authorized: bool) -> bool:
    return bool(authorized)


def can_record_payment(*, provider_confirmed: bool) -> bool:
    return bool(provider_confirmed)
