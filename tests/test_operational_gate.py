from platform_foundation.operational_gate import OperationalGate
from platform_foundation.runtime import PlatformRuntime


def test_operational_gate_requires_started_runtime():
    runtime = PlatformRuntime()
    report = OperationalGate(runtime).check()
    assert report.ready is False
    assert report.checks["runtime_started"] is False


def test_operational_gate_passes_after_start():
    runtime = PlatformRuntime()
    runtime.start()
    report = OperationalGate(runtime).check()
    assert report.ready is True
    assert report.health_passed is True


def test_operational_gate_reports_failed_health():
    runtime = PlatformRuntime()
    runtime.start()
    runtime.stop()
    report = OperationalGate(runtime).check()
    assert report.ready is False
    assert report.checks["health"] is False
