"""Runtime-neutral registry for approved external adapters.

Adapters are references/interfaces, not bundled third-party source. A project
must pass the license and Brain verification gates before activation.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class AdapterSpec:
    project: str
    repository: str
    capability: str
    entrypoint: str
    activation: str = "disabled-until-verified"

REGISTRY = [
    AdapterSpec("Taiwan-LLM", "MiuLab/Taiwan-LLM", "traditional-chinese-llm",
                "external command/API adapter"),
    AdapterSpec("taiwan-asr-toolkit", "thc1006/taiwan-asr-toolkit", "speech-to-text",
                "external ASR service/process adapter"),
    AdapterSpec("Taiwan-Tongues-ASR-CE", "adi-gov-tw/Taiwan-Tongues-ASR-CE",
                "multilingual-taiwan-asr", "external API adapter"),
]

def enabled() -> list[AdapterSpec]:
    return [x for x in REGISTRY if x.activation == "verified"]
