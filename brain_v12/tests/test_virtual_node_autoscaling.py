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
    def test_queue_scales_out_brain_owned_node_when_existing_node_is_incapable(self):
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
                original.capabilities = {"gpu"}
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

    def test_queued_task_survives_queue_restart_and_executes_on_software_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_path = os.path.join(tmp, "tasks.db")
            common_env = {
                "BRAIN_VIRTUAL_MIN_BLADES": "0",
                "BRAIN_VIRTUAL_MAX_BLADES": "1",
                "BRAIN_VIRTUAL_RAM_BYTES_PER_BLADE": "65536",
            }
            with patch.dict(os.environ, {**common_env, "BRAIN_VIRTUAL_AUTOSCALE": "0"}, clear=False):
                first_chassis = BladeChassis()
                first_queue = VirtualTaskQueue(
                    first_chassis, ResourceManager(), max_workers=1, store_path=store_path
                )
                try:
                    task = first_queue.submit([("HALT",)], required_capabilities={"cpu"})
                    self.assertIn(task.status, {"QUEUED", "WAITING"})
                    persisted = first_queue.store.get(task.task_id)
                    self.assertIsNotNone(persisted)
                    self.assertIn(persisted["status"], {"QUEUED", "WAITING"})
                finally:
                    first_queue.shutdown()

            with patch.dict(os.environ, {**common_env, "BRAIN_VIRTUAL_AUTOSCALE": "1"}, clear=False):
                recovered_chassis = BladeChassis()
                recovered_queue = VirtualTaskQueue(
                    recovered_chassis, ResourceManager(), max_workers=1, store_path=store_path
                )
                try:
                    deadline = time.monotonic() + 3
                    current = None
                    while time.monotonic() < deadline:
                        current = recovered_queue.get(task.task_id)
                        if current and current.status in {"COMPLETED", "FAILED"}:
                            break
                        time.sleep(0.02)
                    self.assertIsNotNone(current)
                    self.assertEqual(current.status, "COMPLETED", getattr(current, "result", None))
                    self.assertTrue(current.blade_id)
                    self.assertEqual(recovered_queue.store.get(task.task_id)["status"], "COMPLETED")
                finally:
                    recovered_queue.shutdown()

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
                current = None
                while time.monotonic() < deadline:
                    current = queue.get(task.task_id)
                    if current and current.status in {"COMPLETED", "FAILED"}:
                        break
                    time.sleep(0.02)
                self.assertIsNotNone(current)
                self.assertEqual(current.status, "COMPLETED", getattr(current, "result", None))
                self.assertTrue(current.blade_id)
            finally:
                queue.shutdown()


if __name__ == "__main__":
    unittest.main()
