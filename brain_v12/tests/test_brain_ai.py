import unittest

from brain_v12.brain.brain_ai import BrainAI
from brain_v12.brain.model_router import ModelRouter


class FakeProvider:
    def status(self):
        return {"provider": "fake", "configured": True, "model": "test"}

    def respond(self, user_text, context="", instructions=""):
        return {"ok": True, "provider": "fake", "model": "test",
                "reply": f"Brain received: {user_text}",
                "response_id": "test-response"}


class SupervisorToolProvider(FakeProvider):
    def __init__(self):
        self.calls = 0

    def respond(self, user_text, context="", instructions=""):
        self.calls += 1
        if self.calls == 1:
            return {"ok": True, "provider": "fake", "model": "test",
                    "tool_calls": [{"name": "supervisor.solve",
                                    "params": {"goal": "inspect the current state"}}]}
        return {"ok": True, "provider": "fake", "model": "test",
                "reply": "A safe step ran, but the user objective is not yet verified."}


class FakeMemory:
    def memories(self):
        return [{"key": "project", "value": "Electronic Brain"}]


class TestBrainAI(unittest.TestCase):
    def setUp(self):
        self.ai = BrainAI(FakeProvider(), FakeMemory(), None)

    def test_model_router_selects_and_falls_back(self):
        router = ModelRouter(default_model="primary", fallback_models=["backup"])
        calls = []
        def primary(payload):
            calls.append("primary")
            return {"ok": False, "error": "temporary"}
        def backup(payload):
            calls.append("backup")
            return {"ok": True, "result": {"reply": "backup reply", "response_id": "backup-1"}}
        router.register("primary", primary, tasks=["chat"], priority=1)
        router.register("backup", backup, tasks=["chat"], priority=2)
        result = router.respond("hello")
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "backup")
        self.assertTrue(result["routing"]["fallback_used"])
        self.assertEqual(calls, ["primary", "backup"])

    def test_model_router_fails_closed_when_no_model_exists(self):
        router = ModelRouter()
        result = router.respond("hello")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "NO_MODEL_AVAILABLE")

    def test_brain_status_exposes_model_router(self):
        router = ModelRouter(default_model="primary")
        router.register("primary", lambda payload: {"ok": True, "result": {"reply": "x"}}, tasks=["chat"])
        ai = BrainAI(FakeProvider(), FakeMemory(), None, model_router=router)
        self.assertTrue(ai.status()["model_router"]["ok"])

    def test_model_router_evidence_is_exposed(self):
        class Router:
            def respond(self, *args, **kwargs):
                return {"ok": True, "provider": "router-model", "model": "router-model", "reply": "ok", "routing": {"task": "chat", "selected_model": "router-model", "fallback_used": False}, "evidence": {"type": "model_routing", "selected": "router-model"}}
            def status(self): return {"enabled": True}
        brain = BrainAI(provider=FakeProvider(), model_router=Router())
        result = brain.chat("hello")
        self.assertTrue(result.ok)
        self.assertEqual(result.model, "router-model")
        self.assertTrue(any(x.get("type") == "model_routing" for x in result.evidence))

    def test_status_exposes_brain_layer(self):
        data = self.ai.status()
        self.assertEqual(data["name"], "Brain AI")
        self.assertTrue(data["memory_enabled"])

    def test_chat_returns_provider_evidence(self):
        result = self.ai.chat("مرحبا")
        self.assertTrue(result.ok)
        self.assertIn("Brain received", result.reply)
        self.assertEqual(result.evidence[0]["response_id"], "test-response")

    def test_high_risk_tool_requires_approval(self):
        self.ai.register_tool("danger", "test", lambda _: {"ok": True}, risk="high")
        result = self.ai.execute_tool("danger")
        self.assertEqual(result["status"], "WAITING_APPROVAL")

    def test_tool_result_is_explicit(self):
        self.ai.register_tool("status", "test",
                              lambda _: {"ok": True, "status": "COMPLETED"})
        result = self.ai.execute_tool("status")
        self.assertEqual(result["status"], "COMPLETED")

    def test_supervisor_chat_runs_pipeline_and_exposes_action_and_objective_evidence(self):
        class Solver:
            def __init__(self): self.goals = []
            def solve(self, goal):
                self.goals.append(goal)
                return {
                    "ok": True, "status": "IN_PROGRESS", "run_id": "PS-test",
                    "objective_verified": False,
                    "supervisor_job": {"job_id": "job-test", "status": "blocked"},
                    "execution": {"status": "COMPLETED", "solution_run": {
                        "attempts": [{"alternative_id": "state.read", "status": "VERIFIED"}],
                    }},
                    "verification": {"status": "VERIFIED", "evidence": "tool://step/hash"},
                }

        provider = SupervisorToolProvider()
        ai = BrainAI(provider)
        solver = Solver()
        ai.connect_supervisor(solver)
        result = ai.chat("inspect the current state")
        self.assertTrue(result.ok)
        self.assertEqual(solver.goals, ["inspect the current state"])
        supervisor_evidence = next(x for x in result.evidence if x["type"] == "supervisor_execution")
        self.assertFalse(supervisor_evidence["objective_verified"])
        self.assertEqual(supervisor_evidence["evidence_ref"], "tool://step/hash")
        call = next(x for x in result.tool_calls if x["tool"] == "supervisor.solve")
        self.assertFalse(call["verified"])

    def test_supervisor_tool_rejects_empty_goal(self):
        self.ai.connect_supervisor(type("Solver", (), {"solve": lambda self, goal: self.fail("must not run")})())
        result = self.ai.execute_tool("supervisor.solve", {"goal": "  "})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "EMPTY_GOAL")

    def test_full_github_tool_surface_is_registered(self):
        from brain_v12.github_capability_registry import GITHUB_TOOLS
        for name in GITHUB_TOOLS:
            self.assertIn("github.tool." + name, self.ai.tools)
        self.assertEqual(sum(1 for name in self.ai.tools if name.startswith("github.tool.")), len(GITHUB_TOOLS))

    def test_chatgpt_capability_registry_is_available(self):
        result = self.ai.execute_tool("chatgpt.capabilities")
        self.assertTrue(result["ok"])
        names = {item["name"] for item in result["tools"]}
        self.assertIn("web", names)
        self.assertIn("files", names)
        self.assertIn("github", names)

    def test_chatgpt_discovery_selects_host_capability(self):
        result = self.ai.execute_tool("chatgpt.discover", {"query": "ابحث في الويب عن معلومات حديثة"})
        self.assertTrue(result["ok"])
        self.assertTrue(result["candidates"])
        self.assertEqual(result["candidates"][0]["tool"], "web")

    def test_github_mutation_surface_remains_approval_gated(self):
        result = self.ai.execute_tool("github.tool.update_file", {"method": "PUT", "path": "/repos/o/r/contents/x"})
        self.assertEqual(result["status"], "WAITING_APPROVAL")



    def test_live_chat_attaches_twenty_layer_trace_to_response_evidence(self):
        result = self.ai.chat("trace this request")
        traces = [item for item in result.evidence if item.get("type") == "brain_gpt_20_layer_trace"]
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["architecture_layers"], 20)
        self.assertEqual(len(traces[0]["layers"]), 20)
        self.assertFalse(traces[0]["execution_performed_by_trace"])
        by_key = {item["key"]: item for item in traces[0]["layers"]}
        self.assertEqual(by_key["input_gateway"]["status"], "COMPLETED")
        self.assertEqual(by_key["identity_access"]["status"], "NOT_WIRED")
        self.assertEqual(by_key["memory_consolidation"]["status"], "NOT_WIRED")


if __name__ == "__main__":
    unittest.main()
