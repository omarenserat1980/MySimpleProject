"""Regression tests for Brain Git workflow routes using the initialized service."""
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain_git import api
from brain_v12.brain_git.service import BrainGitService


class BrainGitWorkflowRouteTests(unittest.TestCase):
    def test_default_router_can_create_and_list_workflows(self):
        previous_key = os.environ.get("BRAIN_CONTROL_KEY")
        os.environ["BRAIN_CONTROL_KEY"] = "test-control-key"
        try:
            with tempfile.TemporaryDirectory() as directory:
                service = BrainGitService(directory)
                app = FastAPI()
                # Exercise router()'s default-service path without writing into
                # the repository or the developer's normal runtime directory.
                with patch.object(api, "BrainGitService", return_value=service):
                    app.include_router(api.router())
                client = TestClient(app)

                created = client.post(
                    "/api/brain-git/workflows",
                    headers={"X-Brain-Control-Key": "test-control-key"},
                    json={"name": "routine-check", "command": ["python", "--version"]},
                )
                self.assertEqual(created.status_code, 200, created.text)
                workflow_id = created.json()["workflow"]["id"]

                listed = client.get("/api/brain-git/workflows")
                self.assertEqual(listed.status_code, 200, listed.text)
                self.assertTrue(
                    any(item.get("id") == workflow_id for item in listed.json()["workflows"])
                )

                fetched = client.get(f"/api/brain-git/workflows/{workflow_id}")
                self.assertEqual(fetched.status_code, 200, fetched.text)
                self.assertEqual(fetched.json()["workflow"]["command"], ["python", "--version"])
        finally:
            if previous_key is None:
                os.environ.pop("BRAIN_CONTROL_KEY", None)
            else:
                os.environ["BRAIN_CONTROL_KEY"] = previous_key


if __name__ == "__main__":
    unittest.main()
