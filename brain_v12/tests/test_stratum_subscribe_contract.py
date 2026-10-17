import unittest
from brain_v12.brain.stratum_subscribe_contract import SubscribeResultError, parse_subscribe_result

class SubscribeResultContractTests(unittest.TestCase):
    def test_valid_result_preserves_extranonce_bytes_and_size(self):
        result = parse_subscribe_result([[['mining.notify', 'sub-id']], 'A1b2', 4])
        self.assertEqual(result['extranonce1'], 'a1b2')
        self.assertEqual(result['extranonce1_bytes'], 2)
        self.assertEqual(result['extranonce2_size'], 4)
        self.assertFalse(result['session_authorized'])
        self.assertFalse(result['pool_trust_verified'])

    def test_rejects_bad_result_shapes_and_types(self):
        for value in (None, [], [[], 'abc', 4], [[], 'zz', 4], [[], '00', True], [[], '00', 0], [[['x']], '00', 1]):
            with self.subTest(value=value), self.assertRaises(SubscribeResultError):
                parse_subscribe_result(value)

if __name__ == '__main__':
    unittest.main()
