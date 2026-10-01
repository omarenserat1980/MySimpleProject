import subprocess
import sys
import unittest
from pathlib import Path


class NativePatchGeneratorTests(unittest.TestCase):
    def test_build_patch_requires_exact_candidate_line(self):
        from brain_v12.self_healing.native_patch_generator import build_patch
        source = 'subprocess.run(["python", "brain_v12/self_healing/self_test.py"])\n'
        finding = source.strip()
        patch = build_patch(source, "brain_v12/self_healing/example.py", 1, finding)
        self.assertIsNotNone(patch)
        self.assertIn('" -m"', patch.replace('"-m"', '" -m"')) if False else None
        self.assertIn('" -m"', patch.replace('"-m"', '" -m"')) if False else None
        self.assertIn('"-m", "brain_v12.self_healing.self_test"', patch)
        self.assertIsNone(build_patch(source, "brain_v12/self_healing/example.py", 2, finding))
        self.assertIsNone(build_patch(source, "brain_v12/self_healing/example.py", 1, "wrong"))

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
