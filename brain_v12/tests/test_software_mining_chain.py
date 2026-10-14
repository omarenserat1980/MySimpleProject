import unittest

from brain_v12.brain.software_mining_chain import SoftwareMiningChain


class SoftwareMiningChainTests(unittest.TestCase):
    def test_chain_can_grow_without_fixed_logical_limit(self):
        chain = SoftwareMiningChain()
        for i in range(100):
            chain.append(f"node-{i:03d}")
        snap = chain.snapshot()
        self.assertEqual(snap["logical_node_count"], 100)
        self.assertTrue(snap["unbounded_logical_topology"])
        self.assertFalse(snap["extra_compute_created_by_nodes"])
        self.assertEqual(snap["verified_revenue_btc"], 0.0)

    def test_revenue_stays_blocked_without_real_evidence(self):
        chain = SoftwareMiningChain()
        chain.append("node-000")
        result = chain.revenue_gate()
        self.assertFalse(result["revenue_realized"])
        self.assertEqual(result["status"], "BLOCKED_NO_REAL_POOL_EVIDENCE")

    def test_pool_without_payout_is_not_revenue(self):
        chain = SoftwareMiningChain()
        chain.append("node-000")
        result = chain.revenue_gate(real_pool_evidence=True)
        self.assertFalse(result["revenue_realized"])
        self.assertEqual(result["status"], "BLOCKED_NO_BTC_PAYOUT_EVIDENCE")

    def test_both_evidence_gates_open(self):
        chain = SoftwareMiningChain()
        result = chain.revenue_gate(real_pool_evidence=True, payout_evidence=True)
        self.assertTrue(result["revenue_realized"])


if __name__ == "__main__":
    unittest.main()
