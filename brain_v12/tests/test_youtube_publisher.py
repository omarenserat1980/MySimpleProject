import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from brain_v12.brain.youtube_publisher import YouTubePublisher


class Store:
    def __init__(self):
        self.rows = []

    def event(self, kind, payload):
        self.rows.append((kind, payload))


class YouTubePublisherTests(unittest.TestCase):
    def test_validation_rejects_missing_media(self):
        store = Store()
        publisher = YouTubePublisher(store)
        result = publisher.validate_release("Test", "/does/not/exist.mp4")
        self.assertFalse(result["ok"])
        self.assertFalse(result["checks"]["media_path"])

    def test_publish_requires_oauth_provider(self):
        store = Store()
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            publisher = YouTubePublisher(store)
            with patch("brain_v12.brain.youtube_publisher.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "1.0\n"
                result = publisher.publish_cinematic_release("Test", media_path=f.name)
        self.assertEqual(result["status"], "YOUTUBE_OAUTH_PROVIDER_NOT_CONNECTED")

    def test_publish_uploads_and_verifies_video(self):
        store = Store()
        credentials = object()
        with tempfile.NamedTemporaryFile(suffix=".mp4") as media:
            publisher = YouTubePublisher(store, lambda: credentials)
            with patch("brain_v12.brain.youtube_publisher.subprocess.run") as run,                  patch("brain_v12.brain.youtube_publisher.build") as build:
                run.return_value.returncode = 0
                run.return_value.stdout = "12.5\n"

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
                    "Test", "desc", media.name, ["brain"], "private"
                )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "PUBLISHED_VERIFIED")
        self.assertEqual(result["video_id"], "abc123")
        self.assertTrue(any(k == "YOUTUBE_UPLOAD_STARTED" for k, _ in store.rows))
        self.assertTrue(any(k == "YOUTUBE_RELEASE_PUBLISHED_VERIFIED" for k, _ in store.rows))


if __name__ == "__main__":
    unittest.main()
