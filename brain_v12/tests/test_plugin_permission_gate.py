from brain_v12.brain.permissions import PermissionGate
from brain_v12.brain.plugin_manager import PluginManager


def test_plugin_without_permissions_can_be_enabled():
    manager = PluginManager()
    manager.register("reader", "Reader", "1.0")
    result = manager.enable("reader")
    assert result["ok"] is True
    assert result["status"] == "enabled"


def test_plugin_with_permissions_fails_closed_without_gate():
    manager = PluginManager()
    manager.register("device", "Device", "1.0", permissions=["device_agent"])
    result = manager.enable("device")
    assert result == {
        "ok": False,
        "error": "PERMISSION_GATE_UNAVAILABLE",
        "required_permissions": ["device_agent"],
    }


def test_plugin_enable_requires_every_declared_permission():
    gate = PermissionGate()
    gate.grant("device_agent")
    manager = PluginManager(permission_gate=gate)
    manager.register("device", "Device", "1.0", permissions=["device_agent", "developer"])
    result = manager.enable("device")
    assert result["ok"] is False
    assert result["error"] == "PLUGIN_PERMISSION_DENIED"
    assert result["missing_permissions"] == ["developer"]
    assert manager.status()[0]["status"] == "disabled"


def test_dangerous_plugin_permission_requires_explicit_approval():
    gate = PermissionGate()
    gate.grant("publish")
    manager = PluginManager(permission_gate=gate)
    manager.register("publisher", "Publisher", "1.0", permissions=["publish"])
    result = manager.enable("publisher")
    assert result["ok"] is False
    assert result["error"] == "PLUGIN_PERMISSION_DENIED"
    assert result["approval_required"] is True


def test_plugin_can_be_enabled_after_permissions_are_granted():
    gate = PermissionGate()
    gate.grant("device_agent")
    manager = PluginManager(permission_gate=gate)
    manager.register("device", "Device", "1.0", permissions=["device_agent"])
    result = manager.enable("device")
    assert result["ok"] is True
    assert result["permissions_checked"] is True


def test_unknown_plugin_is_not_enabled():
    result = PluginManager().enable("missing")
    assert result == {"ok": False, "error": "PLUGIN_NOT_FOUND"}
