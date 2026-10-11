"""Regression tests for the cloud-pool and browser-dashboard contracts.

These tests intentionally use deterministic measured-host data. They prove
router/UI wiring and bounded planning contracts, not a live ASUS deployment.
"""
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.device_cloud_pool import CloudNode, DeviceCloudPool
from brain_v12.brain.device_cloud_pool_api import build_router


class FakeBridge:
    def executor_capacities(self):
        return []


def measured_host():
    return CloudNode(
        node_id="ci-measured-host",
        role="compute_host",
        platform="linux",
        online=True,
        healthy=True,
        cpu_cores=8.0,
        memory_mb=8192,
        disk_mb=20480,
        source="local_host_measurement",
        observed=True,
        capabilities=("python.test", "code.build", "device.status", "device.info"),
        metadata={"hostname": "ci-measured-host"},
    )


def _client():
    app = FastAPI()
    pool = DeviceCloudPool(FakeBridge())
    app.include_router(build_router(pool))
    return TestClient(app)


def test_cloud_pool_status_reports_observed_host_and_no_external_cloud():
    with patch(
        "brain_v12.brain.device_cloud_pool.local_host_node",
        side_effect=measured_host,
    ):
        response = _client().get("/api/cloud-pool/status")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "HOST_ONLY_REMOTE_NODE_NOT_OBSERVED"
    assert body["external_cloud_resources_created"] is False
    assert body["execution_mode"] == "DEVICE_BACKED_SOFTWARE_CLOUD"
    host = next(node for node in body["nodes"] if node["role"] == "compute_host")
    assert host["node_id"] == "ci-measured-host"
    assert host["observed"] is True
    assert host["cpu_cores"] == 8.0
    assert host["memory_mb"] == 8192


def test_cloud_pool_plan_is_preview_not_execution():
    with patch(
        "brain_v12.brain.device_cloud_pool.local_host_node",
        side_effect=measured_host,
    ):
        response = _client().post(
            "/api/cloud-pool/plan",
            json={
                "task_id": "ci-resource-plan",
                "capability": "python.test",
                "cpu_cores": 0.5,
                "memory_mb": 256,
                "disk_mb": 128,
                "gpu_count": 0,
                "timeout_seconds": 30,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PLANNED"
    assert body["executor_id"] == "ci-measured-host"
    assert body.get("execution_started", False) is False


def test_hardware_resource_endpoints_are_registered_and_distinguish_logical_capacity():
    with patch(
        "brain_v12.brain.device_cloud_pool.local_host_node",
        side_effect=measured_host,
    ), patch(
        "brain_v12.brain.software_hardware_factory.local_host_node",
        side_effect=measured_host,
    ):
        client = _client()
        status_response = client.get("/api/hardware/status")
        resources_response = client.get("/api/hardware/resources")
        plan_response = client.post(
            "/api/hardware/plan",
            json={
                "task_id": "ci-logical-plan",
                "cpu_cores": 0.25,
                "memory_mb": 128,
                "disk_mb": 64,
            },
        )

    assert status_response.status_code == 200
    status = status_response.json()
    assert status["capacity"]["cpu_cores_physical_observed"] == 8.0
    assert status["capacity"]["memory_mb_physical_total_observed"] == 8192
    assert "not additional physical hardware" in status["resource_semantics"]
    assert status["remote_execution_proven"] is False
    assert resources_response.status_code == 200
    assert resources_response.json()["lease_storage"] == "in_memory_non_durable"
    assert plan_response.status_code == 200
    assert plan_response.json()["status"] == "PLANNED"
    assert plan_response.json()["execution_started"] is False


def test_browser_dashboard_exists_and_documents_live_endpoints():
    web = Path(__file__).resolve().parents[1] / "web"
    dashboard_path = web / "cloud-pool.html"
    index_path = web / "index.html"

    assert dashboard_path.is_file()
    assert index_path.is_file()
    dashboard = dashboard_path.read_text(encoding="utf-8")
    index = index_path.read_text(encoding="utf-8")

    for route in (
        "/api/cloud-pool/status",
        "/api/cloud-pool/plan",
        "/api/hardware/resources",
        "/api/hardware/plan",
        "/api/hardware/allocate",
        "/api/hardware/release",
    ):
        assert route in dashboard
    assert "/cloud-pool.html" in index
    assert "not OS-enforced" in dashboard or "نظام التشغيل" in dashboard
