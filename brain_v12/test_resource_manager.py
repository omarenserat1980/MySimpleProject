import unittest
from .blade_server import BladeChassis
from .brain.resource_manager import ResourceManager, ResourceRequirement

class ResourceManagerTests(unittest.TestCase):
    def test_snapshot_reports_cpu_ram_storage_network_gpu(self):
        chassis=BladeChassis()
        blade=chassis.create_blade({"cpu","ram","storage","network","gpu"},ram_size=1024)
        blade.power_on()
        blade.computer.ram.write(10,7)
        blade.computer.storage.write("/x",b"hello")
        report=ResourceManager().snapshot(blade)
        self.assertEqual(report["cpu"]["cores"],1)
        self.assertEqual(report["ram"]["total_bytes"],1024)
        self.assertEqual(report["ram"]["used_bytes"],1)
        self.assertEqual(report["storage"]["used_bytes"],5)
        self.assertTrue(report["network"]["available"])
        self.assertTrue(report["gpu"]["available"])

    def test_reservation_is_capability_and_capacity_checked(self):
        chassis=BladeChassis()
        blade=chassis.create_blade({"cpu","ram","storage"},ram_size=1024)
        blade.power_on()
        manager=ResourceManager()
        ok=manager.reserve(blade,"task-1",ResourceRequirement(ram_bytes=512,storage_bytes=512))
        self.assertTrue(ok["ok"])
        bad=manager.reserve(blade,"task-2",ResourceRequirement(ram_bytes=2048))
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["status"],"INSUFFICIENT_RESOURCES")

    def test_cluster_inventory(self):
        chassis=BladeChassis()
        a=chassis.create_blade(); a.power_on()
        b=chassis.create_blade(); b.power_on()
        report=ResourceManager().cluster(chassis)
        self.assertEqual(report["blade_count"],2)
        self.assertEqual(report["online"],2)

if __name__=="__main__":
    unittest.main()
