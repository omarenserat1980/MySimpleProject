"""Regression tests for durable workflow dispatch through Brain Git routes."""
import os
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain_git import api
from brain_v12.brain_git.service import BrainGitService
from brain_v12.brain_git.workflow_engine import BrainWorkflowEngine


class FakeExecutionGateway:
    def run(self, argv, capability="brain-internal-execution", cwd=None, timeout=None):
        return {
            "ok": True,
            "returncode": 0,
            "stdout": "EXECUTED:" + " ".join(argv),
            "stderr": "",
            "executor": "test-gateway",
            "authority": "test",
            "verified_executor": True,
        }


class BrainGitWorkflowRouteTests(unittest.TestCase):
    def test_post_workflow_dispatches_to_execution_engine(self):
        previous_key = os.environ.get("BRAIN_CONTROL_KEY")
        os.environ["BRAIN_CONTROL_KEY"] = "test-control-key"
        try:
            with tempfile.TemporaryDirectory() as directory:
                service = BrainGitService(directory)
                engine = BrainWorkflowEngine(directory, execution_gateway=FakeExecutionGateway())
                app = FastAPI()
                app.include_router(api.router(service, engine))
                client = TestClient(app)

                created = client.post(
                    "/api/brain-git/workflows",
                    headers={"X-Brain-Control-Key": "test-control-key"},
                    json={"name": "routine-check", "command": ["python", "--version"]},
                )
                self.assertEqual(created.status_code, 200, created.text)
                workflow_id = created.json()["workflow"]["id"]

                # TestClient executes BackgroundTasks before returning from post().
                fetched = client.get(f"/api/brain-git/workflows/{workflow_id}")
                self.assertEqual(fetched.status_code, 200, fetched.text)
                workflow = fetched.json()["workflow"]
                self.assertEqual(workflow["command"], ["python", "--version"])
                self.assertEqual(workflow["status"], "SUCCESS")
                self.assertEqual(workflow["stdout"], "EXECUTED:python --version")
                self.assertTrue(workflow["verified_executor"])

                listed = client.get("/api/brain-git/workflows")
                self.assertEqual(listed.status_code, 200, listed.text)
                self.assertTrue(
                    any(item.get("id") == workflow_id for item in listed.json()["workflows"])
                )
        finally:
            if previous_key is None:
                os.environ.pop("BRAIN_CONTROL_KEY", None)
            else:
                os.environ["BRAIN_CONTROL_KEY"] = previous_key


if __name__ == "__main__":
    unittest.main()
