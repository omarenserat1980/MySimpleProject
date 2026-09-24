import unittest

from brain_v12.brain.problem_solver import ProblemSolver


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

    def test_retry_is_bounded(self):
        cognitive=FakeCognitive()
        original=cognitive.execute_tool
        calls={"n":0}
        def fail(*args, **kwargs):
            calls["n"] += 1
            return {"ok":False,"status":"FAILED"}
        cognitive.execute_tool=fail
        result=ProblemSolver(cognitive).solve("فشل الاختبار")
        self.assertFalse(result["ok"])
        self.assertEqual(calls["n"], 3)
        self.assertEqual(len(result["attempts"]), 3)


if __name__ == "__main__":
    unittest.main()
