from brain_v12.brain.windows_cloud_gate import verify_windows_cloud_node


def test_windows_cloud_gate_accepts_real_node_evidence():
    result = verify_windows_cloud_node({
        "node_id": "win-cloud-01",
        "provider": "azure",
        "state": "READY",
        "architecture": "x86_64",
        "last_heartbeat": 1234567890,
        "capabilities": ["windows-server-2025", "windows-cloud", "brain-heartbeat"],
    })
    assert result["verified"] is True
    assert result["status"] == "WINDOWS_CLOUD_VERIFIED"


def test_windows_cloud_gate_rejects_missing_heartbeat_capability():
    result = verify_windows_cloud_node({
        "node_id": "win-cloud-01",
        "provider": "azure",
        "state": "READY",
        "architecture": "x86_64",
        "last_heartbeat": 123,
        "capabilities": ["windows-server-2025", "windows-cloud"],
    })
    assert result["verified"] is False
    assert result["reason"] == "WINDOWS_CLOUD_NODE_EVIDENCE_INCOMPLETE"


def test_windows_cloud_gate_rejects_non_windows_architecture():
    result = verify_windows_cloud_node({
        "node_id": "win-cloud-01",
        "provider": "azure",
        "state": "READY",
        "architecture": "arm64",
        "last_heartbeat": 123,
        "capabilities": ["windows-server-2025", "windows-cloud", "brain-heartbeat"],
    })
    assert result["verified"] is False
    assert result["reason"] == "WINDOWS_CLOUD_ARCHITECTURE_INVALID"
