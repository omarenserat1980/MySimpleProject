import unittest
from .virtual_hardware.computer import VirtualComputer
from .virtual_hardware.firmware import VirtualFirmware
from .virtual_hardware.kernel import VirtualKernel
from .virtual_hardware.network import VirtualRouter,VirtualPacket

class VirtualSystemTests(unittest.TestCase):
    def test_firmware_boot(self):
        c=VirtualComputer("test")
        c.power_on()
        r=VirtualFirmware().boot(c)
        self.assertTrue(r["ok"])
        self.assertIn("BOOT_OK",r["boot_log"])

    def test_kernel_process(self):
        k=VirtualKernel()
        p=k.create_process("brain-test")
        self.assertEqual(p.state,"READY")
        self.assertTrue(k.syscall(p.pid,"status")["ok"])
        self.assertTrue(k.terminate(p.pid))
        self.assertEqual(k.processes[p.pid].state,"TERMINATED")

    def test_virtual_network(self):
        a=VirtualComputer("a"); b=VirtualComputer("b")
        router=VirtualRouter()
        router.register("a",a.nic); router.register("b",b.nic)
        r=router.send(VirtualPacket("a","b",b"PING"))
        self.assertTrue(r["ok"])
        self.assertEqual(b.nic.receive(),b"PING")

if __name__=="__main__": unittest.main()
