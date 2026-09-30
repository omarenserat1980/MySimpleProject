from brain_v12.taiwan_open_source.adapter_registry import REGISTRY, enabled
from brain_v12.taiwan_open_source.asr_adapter import TaiwanASRAdapter

def test_registry_contains_core_adapters():
    assert len(REGISTRY) >= 3
    assert enabled() == []

def test_asr_is_safe_when_unconfigured():
    result = TaiwanASRAdapter().transcribe("sample.wav")
    assert result["status"] == "UNCONFIGURED"
