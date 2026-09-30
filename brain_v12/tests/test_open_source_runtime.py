import os
import tempfile
import unittest
from unittest.mock import patch
from brain_v12.brain.open_source_runtime import collect_status

class RuntimeSafetyTests(unittest.TestCase):
    def test_default_is_no_autostart(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BRAIN_OSS_AUTOSTART", None)
            with tempfile.TemporaryDirectory() as d:
                with patch.dict(os.environ, {"BRAIN_OSS_ARTIFACT_DIR": d}, clear=False):
                    report=collect_status()
                    self.assertFalse(report["autostart_enabled"])
                    self.assertFalse(report["policy"]["download_models"])
                    self.assertFalse(report["policy"]["core_brain_requires_oss"])
                    self.assertEqual(len(report["services"]),4)

if __name__=="__main__":
    unittest.main()
