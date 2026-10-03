import unittest

from brain_v12.brain.problem_solver import ProblemSolver
from brain_v12.brain.solution_engine import Alternative, AlternativeRegistry, SolutionEngine, SourceType


class FakeEvents:
    def __init__(self):
        self.items = []

    def publish(self, name, payload):
        self.items.append((name, payload))


class FakeStore:
    def __init__(self):
        self.mem = []
        self.saved = []
    def memories(self):
        return self.mem
    def save_memory(self, key, value):
        self.saved.append((key, value))
    def state(self):
        return {}
    def set_state(self, state):
        self.last_state = state


class FakePermissions:
    grants = set()


class FakeTasks:
    pass


class FakeDecisions:
    def generate(self, goal):
        return [
            {"id":"safe","action":"plan","expected":"create a verifiable task",
             "risk":"low","requirements":[],"reversible":True,
             "evidence":["goal"],"confidence":0.80,"tool_id":"tasks.create"},
            {"id":"fallback","action":"observe","expected":"read current state",
             "risk":"low","requirements":[],"reversible":True,
             "evidence":["state"],"confidence":0.72,"tool_id":"state.read"},
            {"id":"code","action":"apply_code","expected":"apply code",
             "risk":"high","requirements":["developer_approval"],"reversible":True,
             "evidence":["approval"],"confidence":0.65,"tool_id":"code.apply"},
        ]
    def choose(self, goal, options, permissions):
        return {"status":"DECIDED","goal":goal,"selected":options[0],
                "score":0.8,"reason":"test","alternatives":options[1:]}


class FakeCognitive:
    def __init__(self):
        self.store=FakeStore()
        self.events=FakeEvents()
        self.decisions=FakeDecisions()
        self.permissions=FakePermissions()
        self.tool_calls=[]
    def _state(self, stage, status="RUNNING", **extra):
        self.stage=stage
    def execute_tool(self, tool_id, params=None):
        self.tool_calls.append((tool_id, params))
        return {"ok":True,"status":"COMPLETED","tool":tool_id}


class FakeSupervisor:
    def __init__(self):
        self.transitions=[]
        self.snapshots=[]
    def create(self, task, steps=None):
        return {"job_id":"supervisor-test", "task":task, "status":"running", "steps":steps or []}
    def transition(self, job, phase, status="running", details=None):
        updated={**job,"phase":phase,"status":status,"details":details or {}}
        self.transitions.append(updated)
        return updated
    def snapshot(self, job, outcome=None):
        self.snapshots.append((job,outcome))


class ProblemSolverTests(unittest.TestCase):
    def test_generates_multiple_solutions_and_verifies_selected_solution(self):
        cognitive=FakeCognitive()
        result=ProblemSolver(cognitive).solve("حل المشكلة")
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(len(result["solutions"]), 2)
        self.assertEqual(result["verification"]["status"], "VERIFIED")
        self.assertEqual(result["external_action"], "NOT_CLAIMED")
        self.assertEqual(cognitive.tool_calls[0][0], "tasks.create")
        self.assertTrue(cognitive.store.saved)

    def test_fallback_chain_is_bounded_when_every_option_fails(self):
        cognitive=FakeCognitive()
        original=cognitive.execute_tool
        calls={"n":0}
        def fail(*args, **kwargs):
            calls["n"] += 1
            return {"ok":False,"status":"FAILED"}
        cognitive.execute_tool=fail
        result=ProblemSolver(cognitive).solve("فشل الاختبار")
        self.assertFalse(result["ok"])
        self.assertEqual(calls["n"], 2)
        self.assertEqual(len(result["attempts"]), 2)

    def test_failure_falls_back_to_second_tool_and_verifies(self):
        cognitive=FakeCognitive()
        def fail_primary_then_succeed_fallback(tool_id, params=None):
            cognitive.tool_calls.append((tool_id, params))
            if tool_id == "tasks.create":
                return {"ok":False,"status":"FAILED","tool":tool_id}
            return {"ok":True,"status":"COMPLETED","tool":tool_id}
        cognitive.execute_tool=fail_primary_then_succeed_fallback
        result=ProblemSolver(cognitive).solve("حل المشكلة")
        self.assertTrue(result["ok"])
        self.assertEqual([call[0] for call in cognitive.tool_calls], ["tasks.create", "state.read"])
        self.assertEqual([item["status"] for item in result["execution"]["solution_run"]["attempts"]], ["FAILED", "VERIFIED"])
        self.assertEqual([item["attempt"] for item in result["attempts"]], [1, 2])
        self.assertEqual(result["attempts"][1]["verification"], "VERIFIED")
        self.assertEqual(result["execution"]["tool"], "state.read")
        self.assertTrue(any(name == "SOLUTION_FALLBACK_SELECTED" for name, _ in cognitive.events.items))

    def test_sensitive_action_without_permission_remains_waiting_approval(self):
        cognitive=FakeCognitive()
        cognitive.decisions.generate=lambda _goal: [{
            "id":"sensitive", "action":"apply_code", "expected":"apply code",
            "risk":"high", "requirements":["developer_approval"],
            "reversible":True, "evidence":["approval"], "confidence":0.99,
            "tool_id":"code.apply",
        }]
        cognitive.decisions.choose=lambda goal, options, permissions: {
            "status":"WAITING_APPROVAL", "goal":goal, "selected":options[0],
            "reason":"required_permission", "missing_permissions":["developer_approval"],
            "alternatives":[],
        }
        result=ProblemSolver(cognitive).solve("تعديل حساس")
        self.assertEqual(result["execution"]["status"], "WAITING_APPROVAL")
        self.assertEqual(result["verification"]["status"], "NOT_VERIFIED")
        self.assertEqual(cognitive.tool_calls, [])

    def test_external_adapter_needs_its_own_verifier(self):
        cognitive=FakeCognitive()
        calls=[]
        registry=AlternativeRegistry([
            Alternative("oss.adapter", "Open source adapter", SourceType.OPEN_SOURCE,
                        cost=0, quality=0.99, security_approved=True),
        ])
        solver=ProblemSolver(
            cognitive, solution_engine=SolutionEngine(registry),
            alternative_executors={"oss.adapter": lambda _p, _a: calls.append("ran") or {
                "ok":True,"status":"COMPLETED",
            }},
        )
        result=solver.solve("حل المشكلة")
        self.assertTrue(result["ok"])
        self.assertEqual(calls, ["ran"])
        raw_attempts=result["execution"]["solution_run"]["attempts"]
        self.assertEqual(raw_attempts[0]["alternative_id"], "oss.adapter")
        self.assertEqual(raw_attempts[0]["status"], "UNVERIFIED")
        self.assertEqual(result["execution"]["tool"], "tasks.create")

    def test_supervisor_records_verified_action_without_claiming_goal_completion(self):
        cognitive=FakeCognitive()
        supervisor=FakeSupervisor()
        result=ProblemSolver(cognitive, supervisor=supervisor).solve("حل المشكلة")
        self.assertTrue(result["ok"])
        self.assertEqual(result["verification"]["status"], "VERIFIED")
        self.assertEqual(result["verification"]["scope"], "selected_action")
        self.assertFalse(result["objective_verified"])
        self.assertEqual(result["status"], "IN_PROGRESS")
        self.assertEqual(result["supervisor_job"]["status"], "blocked")
        self.assertEqual(result["supervisor_job"]["details"]["reason"], "IN_PROGRESS")
        self.assertEqual([x["phase"] for x in supervisor.transitions], [
            "discover", "plan", "select_backend", "execute", "verify", "blocked",
        ])
        self.assertFalse(supervisor.snapshots[-1][1]["verified"])


if __name__ == "__main__":
    unittest.main()
