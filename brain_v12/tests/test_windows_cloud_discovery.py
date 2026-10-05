from brain_v12.brain.windows_cloud_discovery import discover_windows_cloud_nodes


def node(ts=1000):
    return {
        "node_id": "win-cloud-01",
        "provider": "cloud",
        "state": "READY",
        "architecture": "x86_64",
        "last_heartbeat": ts,
        "capabilities": ["windows-server-2025", "windows-cloud", "brain-heartbeat"],
    }


def test_discovery_accepts_fresh_verified_node():
    result = discover_windows_cloud_nodes([node()], now=1050, heartbeat_timeout=120)
    assert result["verified"] is True
    assert result["status"] == "WINDOWS_CLOUD_AVAILABLE"


def test_discovery_rejects_stale_node():
    result = discover_windows_cloud_nodes([node()], now=1201, heartbeat_timeout=120)
    assert result["verified"] is False
    assert result["status"] == "WINDOWS_CLOUD_UNAVAILABLE"
    assert result["rejected"][0]["reason"] == "WINDOWS_CLOUD_HEARTBEAT_STALE"
