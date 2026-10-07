import os
import tempfile
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.habitat.api import router


class HabitatApiTests(unittest.TestCase):
    def test_status_is_read_only(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.get("/api/habitat/status")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_mutation_requires_control_key(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.post("/api/habitat/projects", json={"name": "Demo", "kind": "python"})
        self.assertIn(response.status_code, {401, 403})


if __name__ == "__main__":
    unittest.main()
