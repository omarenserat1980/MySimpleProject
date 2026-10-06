from brain_v12.business.customer_execution_router import CustomerExecutionRouter


def test_unknown_backend_is_fail_closed():
    result = CustomerExecutionRouter().inspect("CL-000001")
    assert result["status"] == "BACKEND_NOT_REGISTERED"
    assert result["dispatch_allowed"] is False


def test_registered_backend_must_report_ready():
    router = CustomerExecutionRouter({
        "DEVICE_BRIDGE": lambda: {"ready": False, "reason": "AGENT_OFFLINE"},
    })
    result = router.inspect("CL-000001")
    assert result["status"] == "BACKEND_NOT_READY"
    assert result["dispatch_allowed"] is False


def test_dispatch_never_declares_completion():
    router = CustomerExecutionRouter({
        "DEVICE_BRIDGE": lambda: {"ready": True},
    })
    result = router.dispatch("CL-000001", lambda activity: {"ok": True, "status": "COMPLETED"})
    assert result["status"] == "EXECUTED_AWAITING_VERIFICATION"
    assert result["completion_allowed"] is False


def test_windows_customer_is_scoped_to_windows_backend():
    router = CustomerExecutionRouter({
        "CLOUD_WINDOWS_RUNTIME": lambda: {"ready": True},
    })
    result = router.build_plan("CL-000002")
    assert result["backend"] == "CLOUD_WINDOWS_RUNTIME"
    assert result["dispatch_allowed"] is True
    assert result["completion_allowed"] is False
