import unittest

from brain_v12.brain.portable_resource_orchestrator import (
    ExecutorCapacity,
    LocalResourceBudget,
    PortableResourceOrchestrator,
    ResourceDemand,
    ScheduleRequest,
    intent_digest,
)


class PortableResourceOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.remote_free = ExecutorCapacity(
            executor_id="github-hosted-free",
            capabilities=frozenset({"python.test", "code.build"}),
            cpu_cores=2,
            memory_mb=7000,
            disk_mb=10000,
            tier="FREE_CI",
        )
        self.asus = ExecutorCapacity(
            executor_id="asus-arkan",
            capabilities=frozenset({"python.test", "code.build"}),
            cpu_cores=4,
            memory_mb=3600,
            disk_mb=20000,
            tier="USER_DEVICE",
            is_local=True,
            host_id="arkan",
        )

    def test_prefers_remote_free_executor_over_local_asus(self):
        scheduler = PortableResourceOrchestrator()
        request = ScheduleRequest(
            task_id="run-1",
            capability="python.test",
            demand=ResourceDemand(cpu_cores=1, memory_mb=512, disk_mb=128),
        )
        decision = scheduler.plan(request, [self.asus, self.remote_free])
        self.assertEqual(decision.status, "PLANNED")
        self.assertEqual(decision.executor_id, "github-hosted-free")

    def test_blocks_local_task_over_budget(self):
        scheduler = PortableResourceOrchestrator(
            local_budget=LocalResourceBudget(
                max_cpu_cores_per_task=0.25,
                max_memory_mb_per_task=256,
                max_disk_mb_per_task=512,
                max_concurrent_tasks=1,
            )
        )
        request = ScheduleRequest(
            task_id="render",
            capability="code.build",
            demand=ResourceDemand(cpu_cores=1, memory_mb=1024, disk_mb=128),
        )
        decision = scheduler.plan(request, [self.asus])
        self.assertEqual(decision.status, "BLOCKED_NO_EXECUTOR")
        self.assertEqual(decision.rejected[0]["reason"], "LOCAL_RESOURCE_BUDGET_EXCEEDED")

    def test_paid_executor_never_selected_by_default(self):
        paid = ExecutorCapacity(
            executor_id="paid-vm",
            capabilities=frozenset({"python.test"}),
            cpu_cores=8,
            memory_mb=16000,
            disk_mb=50000,
            tier="PAID_EXTERNAL",
            estimated_cost=0.01,
        )
        request = ScheduleRequest(
            task_id="test",
            capability="python.test",
            demand=ResourceDemand(),
            allow_paid=True,
            max_cost_usd=1.0,
        )
        decision = PortableResourceOrchestrator().plan(request, [paid])
        self.assertEqual(decision.status, "BLOCKED_NO_EXECUTOR")
        self.assertEqual(decision.rejected[0]["reason"], "PAID_DISABLED")

    def test_paid_executor_requires_both_request_and_policy_opt_in(self):
        paid = ExecutorCapacity(
            executor_id="paid-vm",
            capabilities=frozenset({"python.test"}),
            cpu_cores=8,
            memory_mb=16000,
            disk_mb=50000,
            tier="PAID_EXTERNAL",
            estimated_cost=0.25,
        )
        request = ScheduleRequest(
            task_id="test",
            capability="python.test",
            demand=ResourceDemand(),
            allow_paid=True,
            max_cost_usd=0.5,
        )
        scheduler = PortableResourceOrchestrator(default_allow_paid=True)
        self.assertEqual(scheduler.plan(request, [paid]).executor_id, "paid-vm")

    def test_cost_ceiling_is_enforced(self):
        paid = ExecutorCapacity(
            executor_id="paid-vm",
            capabilities=frozenset({"python.test"}),
            cpu_cores=8,
            memory_mb=16000,
            disk_mb=50000,
            tier="PAID_EXTERNAL",
            estimated_cost=0.75,
        )
        request = ScheduleRequest(
            task_id="test",
            capability="python.test",
            demand=ResourceDemand(),
            allow_paid=True,
            max_cost_usd=0.5,
        )
        decision = PortableResourceOrchestrator(default_allow_paid=True).plan(request, [paid])
        self.assertEqual(decision.status, "BLOCKED_NO_EXECUTOR")
        self.assertEqual(decision.rejected[0]["reason"], "COST_LIMIT_EXCEEDED")

    def test_missing_capability_never_reports_success(self):
        request = ScheduleRequest(task_id="x", capability="gpu.inference")
        decision = PortableResourceOrchestrator().plan(request, [self.remote_free])
        self.assertEqual(decision.status, "BLOCKED_NO_EXECUTOR")
        self.assertIsNone(decision.executor_id)

    def test_intent_hash_is_stable(self):
        request = ScheduleRequest(
            task_id="x", capability="python.test", intent={"suite": "smoke"}
        )
        self.assertEqual(intent_digest(request), intent_digest(request))
        self.assertEqual(len(intent_digest(request)), 64)


if __name__ == "__main__":
    unittest.main()
