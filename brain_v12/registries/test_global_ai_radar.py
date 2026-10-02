import json
from pathlib import Path

REGISTRY = Path(__file__).with_name("global_ai_radar.json")

def test_global_ai_radar_registry():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["selection_policy"]["agent_must_not_self_declare_success"] is True
    ids = {item["id"] for item in data["recommended"]}
    required = {"opencode", "openhands", "goose", "qwen_code", "ollama", "vllm", "openshell"}
    assert required <= ids
    for item in data["recommended"]:
        assert item["source"].startswith("https://")
        assert item["why_add"]
