import unittest
from brain_v12.brain.temporary_kvm_options import default_options,rank_options
class TestKVMOptions(unittest.TestCase):
    def test_free_real_kvm_is_preferred(self):
        accepted,rejected=rank_options(default_options())
        self.assertEqual(accepted[0].provider,"brain-owned-executor")
        self.assertTrue(any(x[0]=="render" for x in rejected))
    def test_paid_fallback_is_blocked(self):
        accepted,rejected=rank_options(default_options(),allow_paid=False)
        self.assertTrue(any(x[0]=="azure" and x[1]=="PAID_DISABLED" for x in rejected))
if __name__=="__main__": unittest.main()
