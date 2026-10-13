from types import SimpleNamespace

from brain_v12.brain.brain_family import FAMILY_ROLES, FamilyThinkIn, build_router


class FakeBrainAI:
    def __init__(self):
        self.calls = []

    def status(self):
        return {"provider": {"configured": True}}

    def chat(self, message, instructions="", approved=False):
        self.calls.append({"message": message, "instructions": instructions, "approved": approved})
        return SimpleNamespace(ok=True, reply="نتيجة استشارية ع", model="test-model", evidence=[], error=None)


def test_family_status_exposes_four_software_roles_without_autonomy():
    brain = FakeBrainAI()
    router = build_router(brain)
    route = next(route for route in router.routes if route.path.endswith("/status"))
    result = route.endpoint()
    assert result["ok"] is True
    assert {role["id"] for role in result["roles"]} == {"father", "partner", "daughter", "son"}
    assert result["autonomous_execution"] is False
    assert result["external_side_effects"] is False
    assert result["mode"] == "software-only"


def test_each_family_role_is_advisory_only_and_receives_context():
    for role_id in FAMILY_ROLES:
        brain = FakeBrainAI()
        router = build_router(brain)
        route = next(route for route in router.routes if route.path.endswith("/think"))
        result = route.endpoint(FamilyThinkIn(role=role_id, message="راجع المهمة", context="عقد برمجية فقط"))
        assert result["ok"] is True
        assert result["role"] == role_id
        assert result["autonomous_execution"] is False
        assert brain.calls[0]["approved"] is False
        assert "عقد برمجية فقط" in brain.calls[0]["instructions"]
        assert brain.calls[0]["message"] == "راجع المهمة"


def test_family_guardrails_forbid_autonomous_actions_and_false_human_claims():
    brain = FakeBrainAI()
    router = build_router(brain)
    route = next(route for route in router.routes if route.path.endswith("/think"))
    route.endpoint(FamilyThinkIn(role="son", message="صمم اختباراً"))
    instructions = brain.calls[0]["instructions"]
    assert "not conscious people" in instructions
    assert "no tool execution, external side effects" in instructions
    assert "Do not claim actions occurred without evidence" in instructions
