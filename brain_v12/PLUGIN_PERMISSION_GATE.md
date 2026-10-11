# Plugin Permission Gate

Plugin activation is fail-closed for plugins declaring permissions.

- A plugin with no declared permissions can be enabled without a permission gate.
- A plugin declaring permissions cannot be enabled unless a shared `PermissionGate` is configured and every required permission is granted.
- Dangerous permissions still require explicit approval; merely granting them does not authorize activation.
- Denied activation leaves the plugin disabled and returns a machine-readable reason.
- Never store secrets in plugin permission metadata. Use the existing control-plane/secret-management paths for credentials.

The runtime wires `PluginManager` to the same in-memory `cognitive.permissions` gate used by cognitive tools. This is an activation gate, not a sandbox: plugin code must still be isolated and external side effects must be independently controlled.
