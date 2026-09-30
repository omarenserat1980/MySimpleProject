from brain_v12.taiwan_open_source.qwen_agent_adapter import QwenAgentAdapter
from brain_v12.taiwan_open_source.paddleocr_adapter import PaddleOCRAdapter
from brain_v12.taiwan_open_source.voicera_adapter import VoicEraAdapter

def test_qwen_safe_without_runner():
    assert QwenAgentAdapter().run({"task":"ping"})["status"] == "UNCONFIGURED"

def test_paddle_safe_without_runner():
    assert PaddleOCRAdapter().parse("x.pdf")["status"] == "UNCONFIGURED"

def test_voicera_safe_without_endpoint():
    assert VoicEraAdapter().health()["status"] == "UNCONFIGURED"
