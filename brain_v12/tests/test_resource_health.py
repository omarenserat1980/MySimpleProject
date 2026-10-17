from brain_v12.brain.resource_health import HealthObservation, HealthState


def test_recent_heartbeat_is_healthy():
    assert HealthObservation("device-1", 95, 100, 10).classify() == HealthState.HEALTHY


def test_old_or_missing_heartbeat_is_not_healthy():
    assert HealthObservation("device-1", 80, 100, 10).classify() == HealthState.STALE
    assert HealthObservation("device-1", None, 100, 10).classify() == HealthState.UNKNOWN


def test_future_timestamp_is_invalid():
    assert HealthObservation("device-1", 101, 100, 10).classify() == HealthState.INVALID
