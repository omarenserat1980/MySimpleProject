"""Whole-system readiness report; unknown facts stay unknown."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Readiness:
    software_tests: bool
    evidence_ready: bool
    revenue_pipeline_ready: bool
    payment_provider_ready: bool
    real_funds_known: bool
    autonomous_side_effects_enabled: bool

    @property
    def executable(self) -> bool:
        return (self.software_tests and self.evidence_ready and
                self.revenue_pipeline_ready and self.payment_provider_ready and
                self.real_funds_known and not self.autonomous_side_effects_enabled)

    def blockers(self) -> list[str]:
        checks=[("software_tests",self.software_tests),("evidence_ready",self.evidence_ready),
                ("revenue_pipeline_ready",self.revenue_pipeline_ready),
                ("payment_provider_ready",self.payment_provider_ready),
                ("real_funds_known",self.real_funds_known)]
        return [name for name,ok in checks if not ok]
