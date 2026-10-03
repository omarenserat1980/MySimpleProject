from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ChatGPTToolCapability:
    name: str
    description: str
    mode: str
    risk: str = "low"


CHATGPT_TOOL_CAPABILITIES: List[ChatGPTToolCapability] = [
    ChatGPTToolCapability("web", "Web search, open pages, citations and current information.", "host"),
    ChatGPTToolCapability("files", "Search, read and inspect conversation or library files.", "host"),
    ChatGPTToolCapability("python", "Private Python computation and analysis.", "host"),
    ChatGPTToolCapability("python_user_visible", "User-visible Python artifacts, tables, charts and files.", "host"),
    ChatGPTToolCapability("image_generation", "Generate or edit images.", "host", "medium"),
    ChatGPTToolCapability("github", "GitHub repositories, code, issues, pull requests and Actions.", "native"),
    ChatGPTToolCapability("automations", "Scheduled reminders, searches and recurring tasks.", "host", "medium"),
    ChatGPTToolCapability("remote_desktop", "Authorized remote computer operations.", "host", "high"),
    ChatGPTToolCapability("render", "Cloud service inspection and deployment operations.", "connector", "high"),
    ChatGPTToolCapability("voice_generation", "Generate voice/audio from text.", "host", "medium"),
    ChatGPTToolCapability("website_builder", "Create and publish websites.", "connector", "high"),
    ChatGPTToolCapability("media_generation", "Create media assets through connected media tools.", "connector", "medium"),
]


def capability_catalog() -> Dict[str, object]:
    return {
        "ok": True,
        "version": "1.0",
        "source": "Brain host-tool bridge manifest",
        "execution_model": "host-delegated",
        "note": (
            "Host tools are discoverable by Brain, but Brain's Python runtime cannot "
            "directly invoke ChatGPT host tools unless an explicit bridge/adapter is configured."
        ),
        "tools": [
            {
                "name": item.name,
                "description": item.description,
                "mode": item.mode,
                "risk": item.risk,
                "executable_from_brain_runtime": item.mode == "native",
            }
            for item in CHATGPT_TOOL_CAPABILITIES
        ],
    }


def discover(query: str, limit: int = 10) -> Dict[str, object]:
    text = str(query or "").lower()
    aliases = {
        "بحث": ["web"], "ويب": ["web"], "search": ["web"],
        "ملف": ["files"], "ملفات": ["files"], "document": ["files"],
        "بايثون": ["python", "python_user_visible"], "python": ["python"],
        "صورة": ["image_generation"], "صور": ["image_generation"],
        "github": ["github"], "جت هاب": ["github"],
        "تذكير": ["automations"], "جدولة": ["automations"],
        "صوت": ["voice_generation"],
        "موقع": ["website_builder"],
        "سطح المكتب": ["remote_desktop"],
        "render": ["render"],
    }
    wanted = set()
    for token, names in aliases.items():
        if token in text:
            wanted.update(names)

    scored = []
    for item in CHATGPT_TOOL_CAPABILITIES:
        score = 2 if item.name in wanted else 0
        words = set((item.name + " " + item.description).lower().replace("-", " ").split())
        score += sum(1 for token in text.split() if len(token) > 2 and token in words)
        if score:
            scored.append((score, item))

    scored.sort(key=lambda pair: (-pair[0], pair[1].name))
    return {
        "ok": True,
        "query": text,
        "candidates": [
            {
                "tool": item.name,
                "score": score,
                "mode": item.mode,
                "risk": item.risk,
                "executable_from_brain_runtime": item.mode == "native",
            }
            for score, item in scored[:max(1, int(limit))]
        ],
    }
