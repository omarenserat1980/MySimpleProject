from platform_foundation.open_source_registry import OpenSourceRegistry
from platform_foundation.open_source_gate import OpenSourceCandidate


def test_registry_persists_evaluation(tmp_path):
    registry = OpenSourceRegistry(tmp_path / "registry.json")
    result = registry.evaluate_and_record([
        OpenSourceCandidate("qwen-agent", "china", "Apache-2.0", "1.0.0", True, True, True, True),
        OpenSourceCandidate("unknown", "global", "", "", False, False, False, False),
    ])
    assert result["status"] == "BLOCKED"
    assert "qwen-agent" in result["approved"]
    assert "unknown" in result["blocked"]
    assert (tmp_path / "registry.json").exists()
