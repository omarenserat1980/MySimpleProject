import subprocess
import sys
import unittest
from pathlib import Path


class NativePatchGeneratorTests(unittest.TestCase):
    def test_generator_module_compiles(self):
        path = Path("brain_v12/self_healing/native_patch_generator.py")
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
