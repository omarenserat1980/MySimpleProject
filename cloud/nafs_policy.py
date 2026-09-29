"""Policy adapter for using NafsRuntimeController without bypassing core gates.

Nafs is a behavioral review layer. Security, authorization, validation,
human approval requirements, and deployment policy remain authoritative.
"""
from .nafs_runtime_controller import NafsRuntimeController

class NafsPolicy:
    def __init__(self, controller=None):
        self.controller = controller or NafsRuntimeController()

    def evaluate(self, action: str, **signals) -> dict:
        result = self.controller.preflight(action, **signals)
        # Nafs may block/defer its own behavioral recommendation, but it
        # cannot grant permissions or override an existing security denial.
        return result

    def review(self) -> dict:
        return self.controller.postflight_review()
