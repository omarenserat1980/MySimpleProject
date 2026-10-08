import unittest
from brain_v12.brain.resource_fabric import (
    ResourceFabric, ResourceKind, ResourceRequest, ResourceSpec, ResourceState,
)


class ResourceFabricTests(unittest.TestCase):
    def setUp(self):
        self.fabric = ResourceFabric(lease_seconds=60)
        self.fabric.register_many([
            ResourceSpec("cpu-01", ResourceKind.COMPUTE, "arkan", 96, "core", {"architecture": "x86_64"}),
            ResourceSpec("ram-01", ResourceKind.MEMORY, "arkan", 512, "GB", {"tier": "local"}),
            ResourceSpec("gpu-01", ResourceKind.ACCELERATOR, "arkan", 1, "gpu", {"vendor": "nvidia", "vram_gb": 48}),
            ResourceSpec("nvme-01", ResourceKind.STORAGE, "arkan", 20, "TB", {"media": "nvme"}),
            ResourceSpec("net-01", ResourceKind.NETWORK, "arkan", 25, "Gbps", {"latency_ms": 1}),
        ])

    def test_compose_server_from_resource_intent(self):
        result = self.fabric.compose("brain-max", [
            ResourceRequest(ResourceKind.COMPUTE, 64, "core"),
            ResourceRequest(ResourceKind.MEMORY, 256, "GB"),
            ResourceRequest(ResourceKind.ACCELERATOR, 1, "gpu"),
            ResourceRequest(ResourceKind.STORAGE, 10, "TB"),
            ResourceRequest(ResourceKind.NETWORK, 10, "Gbps"),
        ])
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "COMPOSED")
        self.assertEqual(len(result["resource_ids"]), 5)
        self.assertEqual(self.fabric.inspect()["reservation_count"], 1)

    def test_required_capacity_blocks_without_fake_capacity(self):
        result = self.fabric.compose("too-big", [
            ResourceRequest(ResourceKind.MEMORY, 2048, "GB"),
        ])
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "PLAN_BLOCKED")

    def test_release_returns_capacity(self):
        result = self.fabric.compose("release-me", [
            ResourceRequest(ResourceKind.COMPUTE, 32, "core"),
        ])
        self.assertTrue(result["ok"])
        reservation_id = result["reservation"]["reservation_id"]
        self.assertTrue(self.fabric.release(reservation_id)["ok"])
        again = self.fabric.compose("again", [
            ResourceRequest(ResourceKind.COMPUTE, 32, "core"),
        ])
        self.assertTrue(again["ok"])

    def test_degraded_resource_is_usable_but_offline_is_not(self):
        self.fabric.resources["cpu-01"] = ResourceSpec(
            "cpu-01", ResourceKind.COMPUTE, "arkan", 96, "core",
            {"architecture": "x86_64"}, ResourceState.DEGRADED,
        )
        self.assertTrue(self.fabric.compose("degraded-ok", [
            ResourceRequest(ResourceKind.COMPUTE, 8, "core"),
        ])["ok"])
        self.fabric.resources["cpu-01"] = ResourceSpec(
            "cpu-01", ResourceKind.COMPUTE, "arkan", 96, "core",
            {"architecture": "x86_64"}, ResourceState.OFFLINE,
        )
        self.assertFalse(self.fabric.compose("offline-block", [
            ResourceRequest(ResourceKind.COMPUTE, 8, "core"),
        ])["ok"])


if __name__ == "__main__":
    unittest.main()
