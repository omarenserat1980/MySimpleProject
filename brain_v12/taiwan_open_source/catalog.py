"""Curated Taiwan open-source catalog.

The catalog stores metadata only; Brain never copies third-party code without
an explicit integration decision and license/security verification.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json
from pathlib import Path

@dataclass(frozen=True)
class Project:
    name: str
    repository: str
    category: str
    purpose: str
    license_hint: str
    integration: str
    source_type: str = "public"

PROJECTS = [
    Project("VoicEra", "COSS-India/VoicEra", "india-voice-ai",
            "Self-hosted Indian-language STT/TTS/LLM/telephony voice infrastructure",
            "Apache-2.0", "adapter-only"),
    Project("AI4I-Orchestrate", "COSS-India/ai4i-core", "india-ai-inference",
            "Indic-language ASR/TTS/OCR/NER/translation/LLM inference platform",
            "verify upstream LICENSE", "adapter-only"),
    Project("Vani", "vani-voice/vani", "india-voice-protocol",
            "Indian-language voice agent protocol and middleware",
            "verify upstream LICENSE", "adapter-only"),
    Project("BRAHM-AI", "brahm-ai-official/brahm-ai", "india-multimodal-ai",
            "Multilingual voice, vision, RAG and automation ecosystem",
            "verify upstream LICENSE", "adapter-only"),
    Project("Kotoba-Whisper", "kotoba-tech/kotoba-whisper", "japan-asr",
            "Japanese speech recognition training/evaluation stack",
            "verify upstream LICENSE", "adapter-only"),
    Project("awesome-japanese-llm", "llm-jp/awesome-japanese-llm", "japan-llm-catalog",
            "Curated Japanese LLM, speech and multimodal model catalog",
            "CC0/list; verify each linked model", "catalog-only"),
    Project("Qwen", "QwenLM/Qwen", "china-llm",
            "Alibaba Qwen language-model source and tooling",
            "Apache-2.0 source; model-specific terms apply", "adapter-only"),
    Project("Qwen-Agent", "QwenLM/Qwen-Agent", "china-agents",
            "Agent framework with tools, MCP and code interpreter integrations",
            "Apache-2.0", "adapter-only"),
    Project("PaddleOCR", "PaddlePaddle/PaddleOCR", "china-ocr",
            "Multilingual OCR and document parsing",
            "Apache-2.0", "adapter-only"),
    Project("MinerU", "opendatalab/MinerU", "china-document-ai",
            "PDF/Office document parsing to LLM-ready Markdown/JSON",
            "MinerU Open Source License; additional terms", "adapter-only"),
    Project("Taiwan-LLM", "MiuLab/Taiwan-LLM", "llm",
            "Traditional Mandarin and Taiwan-domain language model resources",
            "verify upstream LICENSE", "adapter-only"),
    Project("taiwan-asr-toolkit", "thc1006/taiwan-asr-toolkit", "asr",
            "Traditional Chinese/Taiwan Mandarin ASR pipeline",
            "verify upstream LICENSE", "adapter-only"),
    Project("Taiwan-Tongues-ASR-CE", "adi-gov-tw/Taiwan-Tongues-ASR-CE", "asr",
            "Multilingual Taiwan ASR: Mandarin, Taiwanese, Hakka and English",
            "verify upstream LICENSE", "adapter-only"),
    Project("ALR-TW", "LucasYeh702/alr-tw", "legal-rag-mcp",
            "Evidence-oriented Taiwan-law research MCP harness",
            "verify upstream LICENSE", "adapter-only"),
    Project("OpenTaiMed", "shin13/opentaimed", "mcp-data",
            "TFDA public-data MCP wrapper with provenance-oriented lookup",
            "verify upstream LICENSE", "adapter-only"),
    Project("taiwan-law-rag-mcp", "Sadivo/taiwan-law-rag-mcp", "legal-rag-mcp",
            "Hybrid retrieval and MCP for Taiwan legal text",
            "verify upstream LICENSE", "adapter-only"),
    Project("opdstar-nhi-mcp", "tatsuju/opdstar-nhi-mcp", "mcp-data",
            "Taiwan NHI data access for AI agents via MCP",
            "verify upstream LICENSE", "adapter-only"),
]

def catalog() -> list[dict]:
    return [asdict(p) for p in PROJECTS]

def write_catalog(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog(), ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    print(json.dumps(catalog(), ensure_ascii=False, indent=2))
