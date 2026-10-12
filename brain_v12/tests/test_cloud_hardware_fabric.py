import unittest

from brain_v12.brain.cloud_hardware_fabric import (
    CloudCapacity, CostPolicy, HardwareRequest, Provider, plan_capacity,
)


class CloudHardwareFabricTests(unittest.TestCase):
    def setUp(self):
        self.request = HardwareRequest(cpu_cores=2, memory_gib=4, storage_gib=64)
        self.free_offer = CloudCapacity(
            provider=Provider.AZURE, sku="free-example",
            cpu_cores=2, memory_gib=4, storage_gib=64,
            free_eligible=True, region="test-region",
        )
        self.paid_offer = CloudCapacity(
            provider=Provider.AZURE, sku="paid-example",
            cpu_cores=4, memory_gib=8, storage_gib=128,
            free_eligible=False, region="test-region",
            estimated_monthly_cost=25.0,
        )

    def test_free_offer_fails_closed_without_verified_entitlement(self):
        plan = plan_capacity(
            self.request, [self.free_offer],
            CostPolicy(free_entitlement_verified=False),
        )
        self.assertEqual(plan.status, "BLOCKED_COST_OR_ENTITLEMENT_GATE")
        self.assertFalse(plan.provisioning_allowed)

    def test_free_offer_can_be_planned_when_entitlement_verified(self):
        plan = plan_capacity(
            self.request, [self.free_offer],
            CostPolicy(free_entitlement_verified=True),
        )
        self.assertEqual(plan.status, "PLAN_READY_NOT_PROVISIONED")
        self.assertEqual(plan.selected.sku, "free-example")
        self.assertFalse(plan.provisioning_allowed)

    def test_paid_offer_requires_explicit_approval_and_cost_ceiling(self):
        denied = plan_capacity(self.request, [self.paid_offer], CostPolicy())
        self.assertEqual(denied.status, "BLOCKED_COST_OR_ENTITLEMENT_GATE")
        allowed = plan_capacity(
            self.request, [self.paid_offer],
            CostPolicy(allow_paid=True, max_monthly_cost=30.0),
        )
        self.assertEqual(allowed.status, "PLAN_READY_NOT_PROVISIONED")
        too_expensive = plan_capacity(
            self.request, [self.paid_offer],
            CostPolicy(allow_paid=True, max_monthly_cost=20.0),
        )
        self.assertEqual(too_expensive.status, "BLOCKED_COST_OR_ENTITLEMENT_GATE")

    def test_gpu_requirement_must_match_offer(self):
        gpu_request = HardwareRequest(
            cpu_cores=2, memory_gib=4, storage_gib=64, gpu_required=True
        )
        plan = plan_capacity(
            gpu_request, [self.free_offer],
            CostPolicy(free_entitlement_verified=True),
        )
        self.assertEqual(plan.status, "BLOCKED_NO_CAPACITY")


if __name__ == "__main__":
    unittest.main()
