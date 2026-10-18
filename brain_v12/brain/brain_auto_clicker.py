"""Safety-first policy core for Brain Auto Clicker.

This is an offline prototype: it does not capture the screen, invoke Android
AccessibilityService, or send real taps. A platform adapter must be added
separately and must preserve the same gates and verification behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Callable


SENSITIVE_LABELS = {
    "pay", "purchase", "buy", "transfer", "send", "delete", "confirm",
    "authorize", "withdraw", "payment", "شراء", "دفع", "تحويل", "حذف",
    "تأكيد", "سحب",
}


class AutoClickerError(ValueError):
    """Raised when an action fails a safety gate."""


@dataclass(frozen=True)
class ClickTarget:
    target_id: str
    label: str
    x: int
    y: int


@dataclass
class AutoClickPolicy:
    enabled: bool = False
    emergency_stop: bool = False
    max_clicks_per_task: int = 5
    allowed_target_ids: set[str] = field(default_factory=set)
    clicks_used: int = 0

    def authorize(self, target: ClickTarget, *, explicit_sensitive_approval: bool = False) -> None:
        if self.emergency_stop:
            raise AutoClickerError("EMERGENCY_STOP_ACTIVE")
        if not self.enabled:
            raise AutoClickerError("AUTO_CLICKER_DISABLED")
        if self.clicks_used >= self.max_clicks_per_task:
            raise AutoClickerError("TASK_CLICK_LIMIT_REACHED")
        if target.target_id not in self.allowed_target_ids:
            raise AutoClickerError("TARGET_NOT_ALLOWLISTED")
        normalized = target.label.casefold()
        if any(label in normalized for label in SENSITIVE_LABELS) and not explicit_sensitive_approval:
            raise AutoClickerError("SENSITIVE_ACTION_APPROVAL_REQUIRED")
        if isinstance(target.x, bool) or isinstance(target.y, bool) or target.x < 0 or target.y < 0:
            raise AutoClickerError("INVALID_SCREEN_COORDINATES")


@dataclass
class BrainAutoClicker:
    policy: AutoClickPolicy
    audit_log: list[dict[str, object]] = field(default_factory=list)

    def execute_one(
        self,
        target: ClickTarget,
        *,
        click_adapter: Callable[[ClickTarget], None],
        verify_adapter: Callable[[ClickTarget], bool],
        explicit_sensitive_approval: bool = False,
    ) -> dict[str, object]:
        """Execute one injected click only after gates; never retries blindly."""
        self.policy.authorize(target, explicit_sensitive_approval=explicit_sensitive_approval)
        entry: dict[str, object] = {
            "timestamp": time(),
            "target_id": target.target_id,
            "action": "click",
            "status": "started",
            "real_device_execution": False,
        }
        self.audit_log.append(entry)
        try:
            click_adapter(target)
            self.policy.clicks_used += 1
            verified = bool(verify_adapter(target))
            entry["status"] = "verified" if verified else "verification_failed"
            entry["result_verified"] = verified
            if not verified:
                entry["stop_reason"] = "EXPECTED_STATE_NOT_OBSERVED"
                self.policy.enabled = False
        except Exception:
            entry["status"] = "adapter_error"
            entry["stop_reason"] = "ADAPTER_ERROR"
            self.policy.enabled = False
            raise
        return dict(entry)

    def stop(self) -> None:
        self.policy.emergency_stop = True
        self.policy.enabled = False
