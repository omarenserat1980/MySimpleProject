import unittest

from brain_v12.execution_fabric_contract import assert_runtime_contract


class ExecutionFabricContractTests(unittest.TestCase):
    def test_contract_is_verified(self):
        result = assert_runtime_contract()
        self.assertTrue(result["verified"])
        self.assertGreaterEqual(len(result["checked_workflows"]), 1)


if __name__ == "__main__":
    unittest.main()
