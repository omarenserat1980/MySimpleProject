from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.computer import VirtualComputer
from brain_v12.virtual_hardware.extended_devices import (
    VirtualBattery, VirtualInputDevice, VirtualModem, VirtualPeripheralFabric,
    VirtualRAID, VirtualRNG, VirtualTPM, VirtualUSBController, VirtualWatchdog,
)


class ExtendedVirtualDeviceTests(unittest.TestCase):
    def test_inventory_is_broad_and_explicitly_software_only(self):
        fabric = VirtualPeripheralFabric()
        inventory = fabric.inventory()
        self.assertEqual(inventory["mode"], "SIMULATED")
        self.assertFalse(inventory["host_hardware_required"])
        self.assertFalse(inventory["external_network_enabled"])
        self.assertGreaterEqual(len(inventory["devices"]), 12)
        self.assertIn("hardware-backed TPM keys", inventory["not_emulated"])
        self.assertFalse(fabric.status()["physical_hardware_used"])

    def test_virtual_computer_exposes_extended_fabric_in_status_and_manifest(self):
        computer = VirtualComputer("peripheral-integrated", ram_size=1024)
        status = computer.status()
        self.assertFalse(status["peripherals"]["physical_hardware_used"])
        self.assertTrue(status["peripherals"]["inventory"]["devices"]["modem"]["present"])
        manifest = computer.hardware_manifest()
        self.assertIn("peripherals", manifest["validation"]["categories"])
        self.assertTrue(computer.validate_configuration()["ok"])

    def test_tpm_measurement_is_deterministic_and_not_hardware_attestation(self):
        a, b = VirtualTPM(), VirtualTPM()
        self.assertEqual(a.extend(0, "bootloader")["digest"], b.extend(0, "bootloader")["digest"])
        quote = a.quote([0, 1])
        self.assertFalse(quote["signed_by_hardware_key"])
        with self.assertRaisesRegex(ValueError, "VTPM_MEASUREMENT_INVALID"):
            a.extend(99, "bad")

    def test_usb_enumeration_and_port_conflict(self):
        usb = VirtualUSBController(port_count=2)
        self.assertTrue(usb.attach(1, "kbd0", "hid")["ok"])
        with self.assertRaisesRegex(RuntimeError, "VUSB_PORT_OCCUPIED"):
            usb.attach(1, "mouse0", "hid")
        with self.assertRaisesRegex(ValueError, "VUSB_DEVICE_CLASS_UNSUPPORTED"):
            usb.attach(2, "unknown0", "unknown")
        self.assertEqual(usb.detach(1)["detached"], "kbd0")

    def test_watchdog_expiration_and_feed(self):
        wd = VirtualWatchdog(timeout_ticks=3)
        wd.arm()
        wd.tick(2)
        self.assertEqual(wd.feed()["remaining_ticks"], 3)
        self.assertFalse(wd.tick(2)["expired_now"])
        expired = wd.tick(1)
        self.assertTrue(expired["expired_now"])
        self.assertFalse(expired["reset_performed"])
        self.assertEqual(wd.expirations, 1)

    def test_rng_is_reproducible_but_not_cryptographic(self):
        a, b = VirtualRNG("seed"), VirtualRNG("seed")
        self.assertEqual(a.bytes(80), b.bytes(80))
        self.assertFalse(a.status()["cryptographically_secure"])
        with self.assertRaisesRegex(ValueError, "VRNG_REQUEST_OUT_OF_RANGE"):
            a.bytes(1_048_577)

    def test_modem_never_transmits_externally(self):
        modem = VirtualModem()
        with self.assertRaisesRegex(RuntimeError, "VMODEM_POWERED_OFF"):
            modem.register()
        modem.power(True)
        modem.register("brain.test")
        modem.connect()
        sent = modem.transmit(b"test")
        self.assertFalse(sent["external_transmission"])
        self.assertFalse(modem.status()["external_network_access"])

    def test_iommu_allow_list_blocks_unmapped_regions(self):
        fabric = VirtualPeripheralFabric()
        self.assertFalse(fabric.iommu.dma_allowed("gpu0", "ram:0"))
        fabric.iommu.map("gpu0", "ram:0")
        self.assertTrue(fabric.iommu.dma_allowed("gpu0", "ram:0"))
        self.assertEqual(fabric.iommu.status()["blocked_requests"], 1)
        self.assertFalse(fabric.iommu.status()["hardware_enforced"])

    def test_raid_capacity_and_degraded_availability(self):
        mirror = VirtualRAID("1", [100, 80])
        self.assertEqual(mirror.capacity_bytes, 80)
        mirror.set_member_health(0, False)
        self.assertTrue(mirror.status()["available"])
        self.assertTrue(mirror.status()["degraded"])
        stripe = VirtualRAID("0", [100, 100])
        stripe.set_member_health(1, False)
        self.assertFalse(stripe.status()["available"])
        with self.assertRaisesRegex(ValueError, "VRAID_MEMBER_COUNT_INVALID"):
            VirtualRAID("5", [100, 100])

    def test_battery_and_input_are_bounded_models(self):
        battery = VirtualBattery(capacity_wh=10, state_of_charge=1)
        result = battery.advance(10, 1800)
        self.assertAlmostEqual(result["state_of_charge"], 0.5)
        self.assertFalse(result["physical_measurement"])
        input_device = VirtualInputDevice(queue_limit=1)
        input_device.push("keyboard", "KEY_A")
        with self.assertRaisesRegex(RuntimeError, "VINPUT_QUEUE_FULL"):
            input_device.push("mouse", "LEFT")
        self.assertEqual(len(input_device.drain()), 1)


if __name__ == "__main__":
    unittest.main()
