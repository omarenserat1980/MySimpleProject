import unittest
from brain_v12.brain.company_operating_system import CompanyOperatingSystem
from brain_v12.brain.service_catalog import catalog

class CompanyOperatingSystemTests(unittest.TestCase):
    def test_units(self): self.assertGreaterEqual(len(CompanyOperatingSystem().units()),7)
    def test_service_map(self):
        mapping=CompanyOperatingSystem().service_map(catalog())
        self.assertEqual(set(mapping),{s["id"] for s in catalog()})
        self.assertNotIn("UNASSIGNED",mapping.values())
    def test_order(self):
        cycle=CompanyOperatingSystem().operating_cycle()
        self.assertLess(cycle.index("VERIFY"),cycle.index("DELIVER"))
        self.assertLess(cycle.index("DELIVER"),cycle.index("LEARN"))
    def test_truth_rules(self):
        rules=CompanyOperatingSystem().truth_rules()
        self.assertIn("delivery_requires_evidence",rules)
        self.assertIn("revenue_requires_payment_evidence",rules)

if __name__=="__main__": unittest.main()
