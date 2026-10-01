import unittest
from .virtual_hardware.computer import VirtualComputer
from .virtual_hardware.firmware import VirtualFirmware
from .virtual_hardware.kernel import VirtualKernel
from .virtual_hardware.network import VirtualRouter,VirtualPacket

class VirtualSystemTests(unittest.TestCase):
    def test_firmware_boot_is_integrated(self):
        c=VirtualComputer("test")
        status=c.power_on()
        self.assertTrue(status["powered"])
        self.assertTrue(status["firmware"]["booted"])
        self.assertIn("BOOT_OK",c.boot_record["boot_log"])
        self.assertEqual(c.boot_record["firmware"],VirtualFirmware.VERSION)
        self.assertEqual(c.boot_record["bootloader"]["status"],"KERNEL_OPTIONAL")
        c.filesystem.write("/boot/kernel.bin",b"KERNEL")
        self.assertTrue(c.filesystem.exists("/boot/kernel.bin"))
        self.assertEqual(c.filesystem.read("/boot/kernel.bin"),b"KERNEL")

    def test_kernel_process_scheduler_is_integrated(self):
        c=VirtualComputer("test")
        c.power_on()
        p=c.create_process("brain-test")
        self.assertEqual(p.state,"READY")
        self.assertTrue(c.syscall(p.pid,"status")["ok"])
        c.kernel.tick(3)
        self.assertEqual(c.kernel.ticks,3)
        self.assertGreaterEqual(c.kernel.processes[p.pid].ticks,1)
        self.assertTrue(c.kernel.terminate(p.pid))

    def test_standalone_kernel_boundary(self):
        k=VirtualKernel()
        p=k.create_process("brain-test")
        self.assertEqual(p.state,"READY")
        self.assertTrue(k.syscall(p.pid,"status")["ok"])
        self.assertTrue(k.terminate(p.pid))

    def test_virtual_network(self):
        a=VirtualComputer("a"); b=VirtualComputer("b")
        router=VirtualRouter()
        router.register("a",a.nic); router.register("b",b.nic)
        r=router.send(VirtualPacket("a","b",b"PING"))
        self.assertTrue(r["ok"])
        self.assertEqual(b.nic.receive(),b"PING")

if __name__=="__main__": unittest.main()
