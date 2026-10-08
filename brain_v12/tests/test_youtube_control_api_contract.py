"""Regression tests for the mounted YouTube Control Plane API.

This file lives under brain_v12/tests because the canonical internal CI suite
executes this directory.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.youtube.router_bundle import router


def _payload():
    return {
        "channel_id": "ci-channel",
        "language": "ar",
        "niche": "ai",
        "audience_fit": 0.9,
        "demand": 0.9,
        "competition": 0.4,
        "production_fit": 0.9,
        "monetization_fit": 0.8,
        "originality_headroom": 0.9,
        "video_id": "ci-video",
        "title_angle": "original-story",
        "expected_demand": 0.9,
        "production_cost": 0.1,
        "production_risk": 0.1,
        "originality": 0.9,
        "production_hours": 2,
        "tool_cost_usd": 1,
        "asset_cost_usd": 0,
        "expected_views": 10000,
        "expected_rpm_usd": 5,
        "success_probability": 0.8,
        "learning_value": 0.8,
        "technical_pass": True,
        "cinematic_pass": True,
        "duration_seconds": 120,
        "has_audio": True,
        "has_video": True,
        "originality_confirmed": True,
        "policy_risk": 0.1,
        "script_fingerprint": "script-ci",
        "asset_fingerprint": "assets-ci",
        "existing_fingerprints": [],
    }


def _client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_mounted_youtube_control_plan_is_read_only():
    response = _client().post("/api/youtube/control/evaluate", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "PUBLISH_THEN_MEASURE"
    assert body["requires_publish_authorization"] is True
    assert body["side_effects"] is False
    assert body["execution_plan"] == [
        "DRAFT", "RENDER", "QC", "PUBLISH", "MEASURE", "LEARN"
    ]


def test_mounted_youtube_control_blocks_duplicate():
    payload = _payload()
    payload["existing_fingerprints"] = [{
        "video_id": "ci-video",
        "niche": "ai",
        "title_angle": "original-story",
        "script_fingerprint": "script-ci",
        "asset_fingerprint": "assets-ci",
    }]
    response = _client().post("/api/youtube/control/evaluate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "BLOCK_DUPLICATE"
    assert body["execution_plan"] == []
    assert body["side_effects"] is False
