import unittest
from .blade_server import BladeChassis,BladeScheduler

PROGRAM=[
    ("MOVI",0,40),
    ("MOVI",1,2),
    ("SUB",0,1),
    ("OUT",0),
    ("HALT",),
]

class BladeServerTests(unittest.TestCase):
    def test_virtual_computer_boot_and_execution(self):
        chassis=BladeChassis()
        blade=chassis.create_blade()
        blade.power_on()
        result=blade.execute(PROGRAM)
        self.assertEqual(result["result"]["output"],[38])
        self.assertTrue(result["result"]["halted"])

    def test_capability_based_selection(self):
        chassis=BladeChassis()
        a=chassis.create_blade({"cpu","ram"})
        b=chassis.create_blade({"cpu","ram","gpu","network"})
        a.power_on(); b.power_on()
        scheduler=BladeScheduler(chassis)
        result=scheduler.dispatch([("MOVI",0,7),("OUT",0),("HALT",)],{"cpu","gpu"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["blade_id"],b.blade_id)

    def test_no_matching_executor(self):
        chassis=BladeChassis()
        blade=chassis.create_blade({"cpu"})
        blade.power_on()
        result=BladeScheduler(chassis).dispatch([("HALT",)],{"cpu","network"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"],"NO_CAPABLE_BLADE")

if __name__=="__main__": unittest.main()
