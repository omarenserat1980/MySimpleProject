"""Isolated authorization policy for device heartbeat requests."""

from collections.abc import Callable


class HeartbeatAuthorizationError(Exception):
    """Raised when a heartbeat request fails its identity/authentication gate."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def authorize_heartbeat_identity(
    header_agent_id: str,
    body_agent_id: str,
    supplied_key: str,
    per_agent_registry_configured: bool,
    authenticate: Callable[[str, str], bool],
    legacy_agent_id: str = "android-termux-v12",
) -> str:
    """Resolve identity and authenticate without silently defaulting in per-agent mode."""
    header_id = (header_agent_id or "").strip()
    body_id = (body_agent_id or "").strip()
    if header_id and body_id and header_id != body_id:
        raise HeartbeatAuthorizationError(401, "DEVICE_AGENT_ID_MISMATCH")

    agent_id = header_id or body_id
    if not agent_id and per_agent_registry_configured:
        raise HeartbeatAuthorizationError(401, "DEVICE_AGENT_ID_REQUIRED")

    agent_id = agent_id or legacy_agent_id
    if not authenticate(supplied_key, agent_id):
        raise HeartbeatAuthorizationError(401, "UNAUTHORIZED_AGENT")
    return agent_id
