from brain_v7.braincore_v2.operational_control_plane import OperationalControlPlane


def test_control_plane_joins_health_and_revenue():
    plane = OperationalControlPlane()
    hb = plane.heartbeat("worker-1", cycle=4)
    assert hb["worker_id"] == "worker-1"
    result = plane.record_revenue(
        source="test",
        external_id="order-1",
        amount_jod=12,
        evidence="verified payment",
        recorded_at=1,
    )
    assert result["status"] == "RECORDED"
    snap = plane.snapshot()
    assert snap["health"]["live_workers"] == 1
    assert snap["revenue"]["verified_revenue_jod"] == 12
