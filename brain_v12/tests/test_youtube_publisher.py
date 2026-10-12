import tempfile
import unittest
from unittest.mock import Mock, patch

from brain_v12.brain.youtube_publisher import YouTubePublisher
from brain_v12.business.cl_000003_master_release_gate import REQUIRED


class Store:
    def __init__(self):
        self.rows = []

    def event(self, kind, payload):
        self.rows.append((kind, payload))


class YouTubePublisherTests(unittest.TestCase):
    @staticmethod
    def valid_release_evidence():
        artifact_sha256 = "a" * 64
        return {
            "film_id": "CL3-FILM-001",
            "film_version": "v1",
            "production_run": "RUN-001",
            "artifact_sha256": artifact_sha256,
            **{
                gate: {
                    "passed": True,
                    "evidence_ref": f"CL3-FILM-001/v1/RUN-001/{gate}/evidence.json",
                    "evidence_sha256": "b" * 64,
                    "reviewed_artifact_sha256": artifact_sha256,
                }
                for gate in REQUIRED
            },
        }

    def test_validation_rejects_missing_media(self):
        store = Store()
        publisher = YouTubePublisher(store)
        result = publisher.validate_release("Test", "/does/not/exist.mp4")
        self.assertFalse(result["ok"])
        self.assertFalse(result["checks"]["media_path"])

    def test_publish_without_master_release_evidence_is_blocked(self):
        store = Store()
        with tempfile.NamedTemporaryFile(suffix=".mp4") as media:
            publisher = YouTubePublisher(store)
            with patch("brain_v12.brain.youtube_publisher.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "1.0\\n"
                result = publisher.publish_cinematic_release("Test", media_path=media.name)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "MASTER_RELEASE_EVIDENCE_REQUIRED")
        self.assertTrue(result["release_blocked"])
        self.assertFalse(any(k == "YOUTUBE_UPLOAD_STARTED" for k, _ in store.rows))

    def test_publish_requires_oauth_provider_after_master_release_passes(self):
        store = Store()
        with tempfile.NamedTemporaryFile(suffix=".mp4") as media:
            publisher = YouTubePublisher(store)
            with patch("brain_v12.brain.youtube_publisher.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "1.0\\n"
                result = publisher.publish_cinematic_release(
                    "Test",
                    media_path=media.name,
                    release_evidence=self.valid_release_evidence(),
                )
        self.assertEqual(result["status"], "YOUTUBE_OAUTH_PROVIDER_NOT_CONNECTED")

    def test_publish_uploads_and_verifies_video_after_master_release_passes(self):
        store = Store()
        credentials = object()
        with tempfile.NamedTemporaryFile(suffix=".mp4") as media:
            publisher = YouTubePublisher(store, lambda: credentials)
            with patch("brain_v12.brain.youtube_publisher.subprocess.run") as run, \\
                 patch("brain_v12.brain.youtube_publisher.build") as build:
                run.return_value.returncode = 0
                run.return_value.stdout = "12.5\\n"

                youtube = Mock()
                build.return_value = youtube
                youtube.videos().insert().execute.return_value = {"id": "abc123"}
                youtube.videos().list().execute.return_value = {
                    "items": [{
                        "snippet": {"title": "Test"},
                        "status": {"privacyStatus": "private"},
                    }]
                }

                result = publisher.publish_cinematic_release(
                    "Test",
                    "desc",
                    media.name,
                    ["brain"],
                    "private",
                    release_evidence=self.valid_release_evidence(),
                )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "PUBLISHED_VERIFIED")
        self.assertEqual(result["video_id"], "abc123")
        self.assertTrue(any(k == "YOUTUBE_UPLOAD_STARTED" for k, _ in store.rows))
        self.assertTrue(any(k == "YOUTUBE_RELEASE_PUBLISHED_VERIFIED" for k, _ in store.rows))


if __name__ == "__main__":
    unittest.main()
