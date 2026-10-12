"""Route-level security and workflow-storage regression tests for Brain Git."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from .api import router
from .service import BrainGitService


CONTROL_KEY = "brain-git-test-control-key"
READ_ROUTES = (
    ("/api/brain-git/status", 200),
    ("/api/brain-git/repositories", 200),
    ("/api/brain-git/repositories/proof", 200),
    ("/api/brain-git/repositories/proof/tree?ref=main", 200),
    ("/api/brain-git/repositories/proof/file?path=README.md&ref=main", 200),
    ("/api/brain-git/repositories/proof/fsck", 200),
    ("/api/brain-git/workflows", 200),
    ("/api/brain-git/workflows/not-a-real-workflow", 404),
    ("/api/brain-git/audit", 200),
)


class BrainGitRouteSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.service = BrainGitService(Path(self.tempdir.name))
        self.service.create_repository("proof")
        app = FastAPI()
        app.include_router(router(self.service))
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.tempdir.cleanup()

    def test_read_routes_reject_missing_key(self):
        with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": CONTROL_KEY}):
            for path, _ in READ_ROUTES:
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 403, response.text)
                    self.assertEqual(response.json()["detail"], "CONTROL_PLANE_AUTH_REQUIRED")

    def test_read_routes_reject_invalid_key(self):
        with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": CONTROL_KEY}):
            for path, _ in READ_ROUTES:
                with self.subTest(path=path):
                    response = self.client.get(path, headers={"X-Brain-Control-Key": "wrong-key"})
                    self.assertEqual(response.status_code, 403, response.text)
                    self.assertEqual(response.json()["detail"], "CONTROL_PLANE_AUTH_REQUIRED")

    def test_read_routes_reject_requests_when_control_plane_is_unconfigured(self):
        with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": ""}):
            for path, _ in READ_ROUTES:
                with self.subTest(path=path):
                    response = self.client.get(path, headers={"X-Brain-Control-Key": CONTROL_KEY})
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertEqual(response.json()["detail"], "CONTROL_PLANE_NOT_CONFIGURED")

    def test_read_routes_accept_valid_key_and_preserve_route_status(self):
        with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": CONTROL_KEY}):
            for path, expected_status in READ_ROUTES:
                with self.subTest(path=path):
                    response = self.client.get(path, headers={"X-Brain-Control-Key": CONTROL_KEY})
                    self.assertEqual(response.status_code, expected_status, response.text)

    def test_workflow_storage_uses_injected_service_root(self):
        with patch.dict(os.environ, {"BRAIN_CONTROL_KEY": CONTROL_KEY}):
            response = self.client.post(
                "/api/brain-git/workflows",
                headers={"X-Brain-Control-Key": CONTROL_KEY},
                json={"name": "test-workflow", "command": [], "metadata": {}},
            )
            self.assertEqual(response.status_code, 200, response.text)
            workflow_id = response.json()["workflow"]["id"]
            stored = Path(self.tempdir.name) / "workflows" / (workflow_id + ".json")
            self.assertTrue(stored.is_file())
            detail = self.client.get(
                "/api/brain-git/workflows/" + workflow_id,
                headers={"X-Brain-Control-Key": CONTROL_KEY},
            )
            self.assertEqual(detail.status_code, 200, detail.text)
            self.assertEqual(detail.json()["workflow"]["name"], "test-workflow")


if __name__ == "__main__":
    unittest.main()
