"""Unit tests for the offline device plugin contract."""
import unittest
from brain_v12.brain.device_plugins import (
    DeviceDescriptor, DiagnosticResult, PluginRegistry, PluginValidationError,
    validate_descriptor,
)

class FakePlugin:
    def __init__(self, descriptor):
        self.descriptor = descriptor
    def diagnose_read_only(self, *, timeout_seconds=5.0):
        return DiagnosticResult(True, "fake-01", "2026-10-14T00:00:00Z", {}, self.descriptor.device_kind)

class DevicePluginTests(unittest.TestCase):
    def test_valid_allowlisted_plugin_registers(self):
        d = DeviceDescriptor("fake", "1.0", "SIMULATOR", frozenset({"read_only_diagnostics"}), "Fake simulator")
        r = PluginRegistry({"fake"}); r.register(FakePlugin(d))
        self.assertEqual(r.get("fake").descriptor, d)

    def test_unallowlisted_plugin_rejected(self):
        d = DeviceDescriptor("fake", "1.0", "ASIC_DEVICE", frozenset({"read_only_diagnostics"}), "Fake ASIC")
        with self.assertRaisesRegex(PluginValidationError, "NOT_ALLOWLISTED"):
            PluginRegistry().register(FakePlugin(d))

    def test_simulator_cannot_claim_signed_hardware_challenge(self):
        d = DeviceDescriptor("fake", "1.0", "SIMULATOR", frozenset({"signed_challenge"}), "Fake")
        with self.assertRaisesRegex(PluginValidationError, "SIMULATOR_CANNOT"):
            validate_descriptor(d)

    def test_unknown_capability_rejected(self):
        d = DeviceDescriptor("fake", "1.0", "FPGA", frozenset({"start_mining"}), "Fake FPGA")
        with self.assertRaisesRegex(PluginValidationError, "UNKNOWN_CAPABILITIES"):
            validate_descriptor(d)

    def test_unsupported_api_version_rejected(self):
        d = DeviceDescriptor("fake", "99.0", "FPGA", frozenset(), "Fake FPGA")
        with self.assertRaisesRegex(PluginValidationError, "VERSION_UNSUPPORTED"):
            validate_descriptor(d)

    def test_duplicate_plugin_id_rejected(self):
        d = DeviceDescriptor("fake", "1.0", "FPGA", frozenset(), "Fake FPGA")
        r = PluginRegistry({"fake"}); r.register(FakePlugin(d))
        with self.assertRaisesRegex(PluginValidationError, "DUPLICATE"):
            r.register(FakePlugin(d))

if __name__ == "__main__":
    unittest.main()
