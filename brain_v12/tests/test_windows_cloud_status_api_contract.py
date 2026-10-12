from brain_v12.brain.windows_cloud_discovery import discover_windows_cloud_nodes


def test_no_nodes_is_unavailable():
    result = discover_windows_cloud_nodes([], now=1000)
    assert result["status"] == "WINDOWS_CLOUD_UNAVAILABLE"
    assert result["verified"] is False
