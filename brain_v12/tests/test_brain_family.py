import json
from types import SimpleNamespace

from brain_v12.brain.brain_family import (
    FAMILY_ROLES, MEMORY_PREFIX, FamilyThinkIn, build_router, restore_missing_family_memories,
)


class FakeBrainAI:
    def __init__(self):
        self.calls = []

    def status(self):
        return {"provider": {"configured": True}}

    def chat(self, message, instructions="", approved=False):
        self.calls.append({"message": message, "instructions": instructions, "approved": approved})
        return SimpleNamespace(ok=True, reply="نتيجة استشارية ع", model="test-model", evidence=[], error=None)


class FakeMemoryStore:
    def __init__(self):
        self.data = {}
        self.events = []

    def memories(self):
        return [{"key": k, "value": v} for k, v in self.data.items()]

    def save_memory(self, key, value):
        self.data[key] = value
        self.events.append(key)


def test_family_status_exposes_four_software_roles_and_memory_status():
    brain, memory = FakeBrainAI(), FakeMemoryStore()
    router = build_router(brain, memory)
    route = next(route for route in router.routes if route.path.endswith("/status"))
    result = route.endpoint()
    assert result["ok"] is True
    assert {role["id"] for role in result["roles"]} == {"father", "partner", "daughter", "son"}
    assert all(role["memory"] == "MISSING" for role in result["roles"])
    assert result["autonomous_execution"] is False
    assert result["external_side_effects"] is False
    assert result["mode"] == "software-only"


def test_restore_creates_missing_memories_without_overwriting_existing_ones():
    memory = FakeMemoryStore()
    preserved = {"role": "partner", "lessons": ["existing lesson"], "custom": "keep me"}
    memory.data[MEMORY_PREFIX + "partner"] = json.dumps(preserved)
    result = restore_missing_family_memories(memory)
    assert result["ok"] is True
    assert set(result["restored"]) == {"father", "daughter", "son"}
    assert result["preserved"] == ["partner"]
    assert json.loads(memory.data[MEMORY_PREFIX + "partner"]) == preserved
    for role_id in FAMILY_ROLES:
        assert MEMORY_PREFIX + role_id in memory.data


def test_restore_without_store_reports_blocker():
    result = restore_missing_family_memories(None)
    assert result["ok"] is False
    assert result["status"] == "MEMORY_STORE_UNAVAILABLE"


def test_family_role_loads_its_persisted_memory_and_remains_advisory():
    brain, memory = FakeBrainAI(), FakeMemoryStore()
    memory.data[MEMORY_PREFIX + "son"] = json.dumps({"role": "son", "lessons": ["test first"]})
    router = build_router(brain, memory)
    route = next(route for route in router.routes if route.path.endswith("/think"))
    result = route.endpoint(FamilyThinkIn(role="son", message="صمم اختباراً", context="عقد برمجية فقط"))
    assert result["ok"] is True
    assert result["role"] == "son"
    assert result["memory_loaded"] is True
    assert brain.calls[0]["approved"] is False
    assert "test first" in brain.calls[0]["instructions"]
    assert "عقد برمجية فقط" in brain.calls[0]["instructions"]


def test_family_guardrails_forbid_autonomous_actions_and_false_human_claims():
    brain = FakeBrainAI()
    router = build_router(brain, FakeMemoryStore())
    route = next(route for route in router.routes if route.path.endswith("/think"))
    route.endpoint(FamilyThinkIn(role="daughter", message="نظمي المعرفة"))
    instructions = brain.calls[0]["instructions"]
    assert "not conscious people" in instructions
    assert "no tool execution, external side effects" in instructions
    assert "Do not claim actions occurred without evidence" in instructions
