import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain.cloud_executor_gate import check


class CloudExecutorGateTests(unittest.TestCase):
    def test_gate_requires_x86_kvm_and_qemu(self):
        with tempfile.TemporaryDirectory() as td:
            out = str(Path(td) / "gate.json")
            with patch("brain_v12.brain.cloud_executor_gate.platform.machine", return_value="x86_64"),                  patch("brain_v12.brain.cloud_executor_gate.Path.exists", return_value=True),                  patch("brain_v12.brain.cloud_executor_gate.os.access", return_value=True),                  patch("brain_v12.brain.cloud_executor_gate.shutil.which", side_effect=lambda x: "/usr/bin/qemu-system-x86_64" if x == "qemu-system-x86_64" else "/usr/bin/python"),                  patch("brain_v12.brain.cloud_executor_gate._run", side_effect=[
                     (True, "QEMU emulator version 9"),
                     (True, "kvm tcg")
                 ]):
                e = check(out)
            self.assertTrue(e["verified"])
            self.assertTrue(Path(out).exists())
            self.assertTrue(json.loads(Path(out).read_text())["verified"])

    def test_gate_fails_without_kvm(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("brain_v12.brain.cloud_executor_gate.platform.machine", return_value="x86_64"),                  patch("brain_v12.brain.cloud_executor_gate.Path.exists", return_value=False),                  patch("brain_v12.brain.cloud_executor_gate.os.access", return_value=False),                  patch("brain_v12.brain.cloud_executor_gate.shutil.which", return_value="/usr/bin/qemu-system-x86_64"),                  patch("brain_v12.brain.cloud_executor_gate._run", side_effect=[
                     (True, "QEMU emulator version 9"),
                     (True, "kvm")
                 ]):
                e = check(str(Path(td) / "gate.json"))
            self.assertFalse(e["verified"])


if __name__ == "__main__":
    unittest.main()
