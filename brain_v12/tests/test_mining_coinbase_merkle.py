import hashlib
import unittest

from brain_v12.brain.mining_coinbase_merkle import assemble_coinbase, fold_merkle_branches


def sha256d(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


class CoinbaseMerkleContractTests(unittest.TestCase):
    def test_coinbase_fragments_are_concatenated_in_given_order(self):
        self.assertEqual(
            assemble_coinbase(coinb1=b"a", extranonce1=b"b", extranonce2=b"c", coinb2=b"d"),
            b"abcd",
        )

    def test_merkle_fold_without_branches_is_coinbase_txid_bytes(self):
        coinbase = b"coinbase transaction test fixture"
        self.assertEqual(fold_merkle_branches(coinbase_tx=coinbase, branches_in_pool_order=[]), sha256d(coinbase))

    def test_merkle_fold_uses_explicit_left_then_right_order(self):
        coinbase = b"coinbase"
        branch = bytes(range(32))
        expected = sha256d(sha256d(coinbase) + branch)
        actual = fold_merkle_branches(coinbase_tx=coinbase, branches_in_pool_order=[branch])
        self.assertEqual(actual, expected)
        self.assertNotEqual(actual, sha256d(branch + sha256d(coinbase)))

    def test_rejects_invalid_coinbase_and_branch_inputs(self):
        with self.assertRaises(ValueError):
            assemble_coinbase(coinb1=b"", extranonce1=b"", extranonce2=b"", coinb2=b"")
        with self.assertRaises(ValueError):
            assemble_coinbase(coinb1="aa", extranonce1=b"", extranonce2=b"x", coinb2=b"")
        with self.assertRaises(ValueError):
            fold_merkle_branches(coinbase_tx=b"x", branches_in_pool_order=[b"short"])
        with self.assertRaises(ValueError):
            fold_merkle_branches(coinbase_tx=b"x", branches_in_pool_order="not-a-list")


if __name__ == "__main__":
    unittest.main()
