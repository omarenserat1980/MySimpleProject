from types import SimpleNamespace

from brain_v12.brain.brain_partner import PARTNER_INSTRUCTIONS, PartnerThinkIn, build_router


class FakeBrainAI:
    def __init__(self):
        self.calls = []

    def status(self):
        return {"provider": {"configured": False}}

    def chat(self, message, instructions="", approved=False):
        self.calls.append({
            "message": message,
            "instructions": instructions,
            "approved": approved,
        })
        return SimpleNamespace(
            ok=True, reply="تحليل مستقل ع", model="test-model",
            evidence=[{"type": "test"}], error=None,
        )


def test_partner_profile_is_advisory_only():
    brain = FakeBrainAI()
    router = build_router(brain)
    status_route = next(route for route in router.routes if route.path.endswith("/status"))
    result = status_route.endpoint()
    assert result["ok"] is True
    assert result["autonomous_execution"] is False
    assert result["external_side_effects"] is False
    assert result["mode"] == "software-only"


def test_partner_think_disables_approval_and_includes_context():
    brain = FakeBrainAI()
    router = build_router(brain)
    think_route = next(route for route in router.routes if route.path.endswith("/think"))
    result = think_route.endpoint(PartnerThinkIn(message="راجع هذه الخطة", context="لا توجد أجهزة؛ عقد برمجية فقط"))
    assert result["ok"] is True
    assert result["autonomous_execution"] is False
    assert brain.calls[0]["approved"] is False
    assert "BRAIN_PARTNER_PERSONA" in brain.calls[0]["instructions"]
    assert "لا توجد أجهزة؛ عقد برمجية فقط" in brain.calls[0]["instructions"]
    assert brain.calls[0]["message"] == "راجع هذه الخطة"


def test_partner_persona_requires_evidence_and_never_claims_human_identity():
    assert "distinguish observed evidence from inference" in PARTNER_INSTRUCTIONS
    assert "without pretending to be a human spouse" in PARTNER_INSTRUCTIONS
    assert "Do not perform external actions" in PARTNER_INSTRUCTIONS
