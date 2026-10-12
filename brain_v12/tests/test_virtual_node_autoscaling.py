from __future__ import annotations

import os
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from brain_v12.blade_server import BladeChassis
from brain_v12.brain.resource_manager import ResourceManager, ResourceRequirement
from brain_v12.brain.virtual_task_queue import VirtualTaskQueue


class VirtualNodeAutoscalingTests(unittest.TestCase):
    def test_queue_scales_out_brain_owned_node_when_existing_node_is_offline(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "BRAIN_VIRTUAL_MIN_BLADES": "1",
            "BRAIN_VIRTUAL_MAX_BLADES": "2",
            "BRAIN_VIRTUAL_RAM_BYTES_PER_BLADE": "65536",
            "BRAIN_VIRTUAL_AUTOSCALE": "1",
        }, clear=False):
            chassis = BladeChassis()
            queue = VirtualTaskQueue(chassis, ResourceManager(), max_workers=1,
                                     store_path=os.path.join(tmp, "tasks.db"))
            try:
                original = next(iter(chassis.blades.values()))
                original.power_off()
                task = SimpleNamespace(
                    required_capabilities={"cpu"},
                    requirement=ResourceRequirement(),
                )
                added = queue._ensure_virtual_capacity(task)
                self.assertIsNotNone(added)
                self.assertEqual(len(chassis.blades), 2)
                self.assertEqual(added.state, "ONLINE")
                self.assertTrue({"cpu", "ram", "storage"}.issubset(added.capabilities))
            finally:
                queue.shutdown()

    def test_empty_queue_creates_software_node_and_executes_without_device_agent(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "BRAIN_VIRTUAL_MIN_BLADES": "0",
            "BRAIN_VIRTUAL_MAX_BLADES": "2",
            "BRAIN_VIRTUAL_RAM_BYTES_PER_BLADE": "65536",
            "BRAIN_VIRTUAL_AUTOSCALE": "1",
        }, clear=False):
            chassis = BladeChassis()
            queue = VirtualTaskQueue(chassis, ResourceManager(), max_workers=1,
                                     store_path=os.path.join(tmp, "tasks.db"))
            try:
                task = queue.submit([("HALT",)], required_capabilities={"cpu"})
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    current = queue.get(task.task_id)
                    if current and current.status in {"COMPLETED", "FAILED"}:
                        break
                    time.sleep(0.02)
                self.assertEqual(current.status, "COMPLETED", getattr(current, "result", None))
                self.assertTrue(current.blade_id)
            finally:
                queue.shutdown()


if __name__ == "__main__":
    unittest.main()
