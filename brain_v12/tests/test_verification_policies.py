import unittest
import tempfile
from pathlib import Path

from brain_v12.brain.verification_policies import verify_capability


class VerificationPolicyTests(unittest.TestCase):
    def test_media_requires_real_artifact(self):
        self.assertFalse(verify_capability("media.render", "not-a-file")["verified"])

    def test_media_accepts_real_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "video.mp4"
            p.write_bytes(b"video")
            evidence = verify_capability("media.render", str(p))
            self.assertTrue(evidence["verified"])
            self.assertIn("SHA256_COMPUTED", evidence["checks"])

    def test_publish_requires_remote_confirmation(self):
        self.assertFalse(verify_capability("publish.youtube", {"published": True})["verified"])
        self.assertTrue(verify_capability(
            "publish.youtube", {"published": True, "remote_id": "yt-123"})["verified"])

    def test_unknown_capability_is_rejected(self):
        self.assertFalse(verify_capability("unknown.capability", {"ok": True})["verified"])


if __name__ == "__main__":
    unittest.main()
