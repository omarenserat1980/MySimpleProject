from __future__ import annotations

from typing import Any


class PluginManager:
    """Small plugin registry that fails closed when a plugin requests permissions."""

    def __init__(self, permission_gate: Any | None = None):
        self.plugins: dict[str, dict[str, Any]] = {}
        self.permission_gate = permission_gate

    def register(self, plugin_id, name, version, capabilities=None, permissions=None):
        if not isinstance(plugin_id, str) or not plugin_id.strip():
            raise ValueError("plugin_id must be a non-empty string")
        required_permissions = sorted({
            permission.strip()
            for permission in (permissions or [])
            if isinstance(permission, str) and permission.strip()
        })
        plugin = {
            "id": plugin_id,
            "name": name,
            "version": version,
            "capabilities": list(capabilities or []),
            "permissions": required_permissions,
            "status": "disabled",
            "health": "unknown",
        }
        self.plugins[plugin_id] = plugin
        return dict(plugin)

    def enable(self, plugin_id):
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            return {"ok": False, "error": "PLUGIN_NOT_FOUND"}

        required = plugin["permissions"]
        if required and self.permission_gate is None:
            return {
                "ok": False,
                "error": "PERMISSION_GATE_UNAVAILABLE",
                "required_permissions": list(required),
            }

        if required:
            decision = self.permission_gate.check(required, approved=False)
            if not decision.get("allowed", False):
                return {
                    "ok": False,
                    "error": "PLUGIN_PERMISSION_DENIED",
                    "required_permissions": list(required),
                    "missing_permissions": list(decision.get("missing", [])),
                    "dangerous_permissions": list(decision.get("dangerous", [])),
                    "approval_required": bool(decision.get("approval_required", False)),
                }

        plugin["status"] = "enabled"
        plugin["health"] = "ready"
        return {"ok": True, **plugin, "permissions_checked": True}

    def disable(self, plugin_id):
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            return {"ok": False, "error": "PLUGIN_NOT_FOUND"}
        plugin["status"] = "disabled"
        plugin["health"] = "unknown"
        return {"ok": True, **plugin}

    def status(self):
        return [dict(plugin) for plugin in self.plugins.values()]
