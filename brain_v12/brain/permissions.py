"""Explicit capability and approval gates."""
DANGEROUS_ACTIONS = {"network_external", "delete", "publish", "credentials", "system_admin"}

class PermissionGate:
    def __init__(self):
        self.grants: set[str] = set()

    def grant(self, capability: str):
        self.grants.add(capability)
        return sorted(self.grants)

    def revoke(self, capability: str):
        self.grants.discard(capability)
        return sorted(self.grants)

    def allowed(self, capability: str) -> bool:
        return capability in self.grants

    def check(self, capabilities: list[str], approved: bool = False):
        missing = [c for c in capabilities if c not in self.grants]
        dangerous = [c for c in capabilities if c in DANGEROUS_ACTIONS]
        return {"allowed": not missing and (not dangerous or approved),
                "missing": missing, "dangerous": dangerous,
                "approval_required": bool(dangerous and not approved)}
