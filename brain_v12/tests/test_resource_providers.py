import unittest
from unittest.mock import patch, mock_open
from brain_v12.brain.resource_fabric import ResourceFabric
from brain_v12.brain.resource_providers import HostProbe, HostResourceProvider


class ResourceProviderTests(unittest.TestCase):
    @patch("brain_v12.brain.resource_providers.platform.system", return_value="Linux")
    @patch("brain_v12.brain.resource_providers.platform.machine", return_value="x86_64")
    @patch("brain_v12.brain.resource_providers.os.cpu_count", return_value=96)
    @patch("brain_v12.brain.resource_providers.shutil.disk_usage")
    def test_linux_probe(self, disk_usage, *_):
        disk_usage.return_value.free = 2 * 1024**4
        with patch("builtins.open", mock_open(read_data="MemTotal:       524288000 kB\n")):
            specs = HostProbe("arkan").probe()
        self.assertEqual(specs[0].capacity, 96)
        self.assertEqual(specs[0].unit, "core")
        self.assertTrue(any(x.kind.value == "memory" for x in specs))

    @patch("brain_v12.brain.resource_providers.platform.system", return_value="Windows")
    @patch.object(HostProbe, "_cmd", side_effect=["96", "512", "2"])
    def test_windows_probe(self, *_):
        specs = HostProbe("arkan").probe()
        self.assertEqual(len(specs), 3)
        self.assertEqual(specs[0].capacity, 96)
        self.assertEqual(specs[1].capacity, 512)

    def test_sync_never_invents_capacity(self):
        fabric = ResourceFabric()
        provider = HostResourceProvider(fabric, "test")
        with patch.object(provider.probe_engine, "probe", return_value=[]):
            result = provider.sync()
        self.assertFalse(result["ok"])
        self.assertEqual(fabric.inspect()["resource_count"], 0)


if __name__ == "__main__":
    unittest.main()
