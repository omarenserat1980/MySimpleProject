from __future__ import annotations

import unittest

from brain_v12.brain.solution_engine import (
    Alternative, AlternativeRegistry, SolutionEngine, SourceType,
)
from brain_v12.brain.task_engine import TaskEngine


class SolutionEngineTests(unittest.TestCase):
    def setUp(self):
        self.registry = AlternativeRegistry([
            Alternative("paid", "Paid service", SourceType.SERVICE, cost=5,
                        capabilities=("build",), security_approved=True),
            Alternative("unsafe", "Unreviewed", SourceType.OPEN_SOURCE,
                        capabilities=("build",), security_approved=False),
            Alternative("local", "Local builder", SourceType.BUILT_IN,
                        capabilities=("build",), platforms=("windows",), quality=.8),
            Alternative("oss", "Open builder", SourceType.OPEN_SOURCE,
                        capabilities=("build",), platforms=("windows",), quality=.7,
                        security_approved=True),
        ])
        self.engine = SolutionEngine(self.registry)

    def test_registry_contract_and_deterministic_free_first_selection(self):
        problem, ranked, rejected = self.engine.rank({
            "description": "build app", "required_capabilities": ["build"],
            "platform": "windows", "max_cost": 20,
        })
        self.assertEqual([x.id for x in ranked], ["local", "oss"])
        self.assertEqual(problem.max_cost, 0)
        self.assertIn({"alternative_id": "paid", "check": "cost", "reason": "cost_not_allowed"}, rejected)
        self.assertTrue(any(x["alternative_id"] == "unsafe" and x["check"] == "security" for x in rejected))
        self.assertTrue(all(x.source_type in SourceType for x in self.registry.list()))

    def test_external_sources_require_explicit_security_approval(self):
        registry = AlternativeRegistry([
            Alternative("unreviewed-service", "Unreviewed service", SourceType.SERVICE),
            Alternative("reviewed-oss", "Reviewed OSS", SourceType.OPEN_SOURCE,
                        security_approved=True),
        ])
        _, ranked, rejected = SolutionEngine(registry).rank("problem")
        self.assertEqual([item.id for item in ranked], ["reviewed-oss"])
        self.assertTrue(any(item["alternative_id"] == "unreviewed-service"
                            and item["check"] == "security" for item in rejected))

    def test_compatibility_gate_excludes_wrong_platform_and_capabilities(self):
        problem, ranked, rejected = self.engine.rank({
            "description": "build app", "required_capabilities": ["build", "deploy"],
            "platform": "linux",
        })
        self.assertEqual(ranked, [])
        self.assertTrue(all(x["check"] == "compatibility" for x in rejected))

    def test_problem_contract_normalizes_direct_problem_instances(self):
        from brain_v12.brain.solution_engine import Problem

        normalized, ranked, _ = self.engine.rank(
            Problem("  build app  ", ("BUILD",), "WINDOWS")
        )
        self.assertEqual(normalized.description, "build app")
        self.assertEqual(normalized.required_capabilities, ("build",))
        self.assertEqual(normalized.platform, "windows")
        self.assertEqual([item.id for item in ranked], ["local", "oss"])

    def test_paid_service_requires_explicit_opt_in_and_budget(self):
        _, denied, _ = self.engine.rank({
            "description": "build app", "required_capabilities": ["build"],
        })
        self.assertNotIn("paid", [x.id for x in denied])
        _, allowed, _ = self.engine.rank({
            "description": "build app", "required_capabilities": ["build"],
            "allow_paid": True, "max_cost": 5,
        })
        self.assertIn("paid", [x.id for x in allowed])
        self.assertEqual([x.id for x in allowed][-1], "paid")

    def test_fallback_attempt_count_has_a_configurable_cap(self):
        registry = AlternativeRegistry([
            Alternative(f"local-{index}", f"Local {index}", quality=.5)
            for index in range(4)
        ])
        engine = SolutionEngine(registry, max_attempts=2)
        calls = []
        result = engine.solve(
            "test", {item.id: (lambda _p, _a, name=item.id: calls.append(name))
                     for item in registry.list()},
            lambda _output, _problem, _alternative: False,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual(result["fallback_chain"], calls)
        self.assertTrue(any(item["event"] == "FALLBACK_LIMIT_REACHED" for item in result["audit"]))

    def test_execution_failure_falls_back_and_verifies_before_completion(self):
        task_engine = TaskEngine()
        task = task_engine.create("build a verified app")

        def fail(_problem, _alternative):
            raise RuntimeError("local compiler unavailable")

        result = task_engine.run_with_alternatives(
            task["id"], self.engine,
            {"description": "build app", "required_capabilities": ["build"], "platform": "windows"},
            {"local": fail, "oss": lambda _p, _a: {"artifact": "app.bin"}},
            lambda output, _p, _a: {"ok": output.get("artifact") == "app.bin",
                                    "evidence_ref": "test://artifact-verified"},
        )
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["evidence_ref"], "test://artifact-verified")
        run = task_engine.tasks[task["id"]]["solution_run"]
        self.assertEqual(run["status"], "VERIFIED")
        self.assertEqual([x["status"] for x in run["attempts"]], ["FAILED", "VERIFIED"])
        self.assertEqual(run["selected"], "oss")
        self.assertEqual(run["audit"][-1]["event"], "COMPLETED")

    def test_failed_verification_does_not_complete_task(self):
        task_engine = TaskEngine()
        task = task_engine.create("build app")
        result = task_engine.run_with_alternatives(
            task["id"], self.engine, "build app",
            {"local": lambda _p, _a: "output", "oss": lambda _p, _a: "output"},
            lambda _o, _p, _a: False,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(task["status"], "FAILED")
        self.assertEqual(task["error"], "NO_ALTERNATIVE_VERIFIED")

    def test_success_without_verification_evidence_is_not_accepted(self):
        task_engine = TaskEngine()
        task = task_engine.create("build app")
        result = task_engine.run_with_alternatives(
            task["id"], self.engine, "build app",
            {"local": lambda _p, _a: "output", "oss": lambda _p, _a: "output"},
            lambda _o, _p, _a: {"ok": True},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(task["status"], "FAILED")

    def test_unexpected_engine_error_marks_task_failed(self):
        class BrokenEngine:
            def solve(self, *_args):
                raise RuntimeError("internal error")

        task_engine = TaskEngine()
        task = task_engine.create("broken engine")
        result = task_engine.run_with_alternatives(
            task["id"], BrokenEngine(), "problem", {}, lambda *_args: True,
        )
        self.assertEqual(result["error"], "SOLUTION_ENGINE_ERROR:RuntimeError")
        self.assertEqual(task["status"], "FAILED")

    def test_verified_result_without_evidence_does_not_leave_task_running(self):
        class EvidenceMissingEngine:
            def solve(self, *_args):
                return {"ok": True, "status": "VERIFIED"}

        task_engine = TaskEngine()
        task = task_engine.create("missing evidence")
        result = task_engine.run_with_alternatives(
            task["id"], EvidenceMissingEngine(), "problem", {}, lambda *_args: True,
        )
        self.assertEqual(result["error"], "VERIFICATION_EVIDENCE_REQUIRED")
        self.assertEqual(task["status"], "FAILED")

    def test_duplicate_registry_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.registry.register(Alternative("local", "Duplicate"))


if __name__ == "__main__":
    unittest.main()
