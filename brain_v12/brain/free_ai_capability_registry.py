"""Free/low-cost AI capability registry for Brain.

The registry is deliberately conservative: a free web tier is not treated as
unlimited, and self-hosted/open models are marked as hardware-limited.
"""
from __future__ import annotations

TOOLS = [
    {
        "id": "google_vids_veo",
        "name": "Google Vids / Veo",
        "kind": "hosted_free_tier",
        "capabilities": ["text_to_video", "image_to_video", "1080p", "editing", "youtube_publish"],
        "free_policy": "limited",
        "automation": "ui_or_workspace",
        "official": "https://blog.google/products-and-platforms/products/workspace/google-vids-updates-lyria-veo/",
        "watch": "https://workspaceupdates.googleblog.com/",
        "brain_use": "prototype_storyboards_and_manual_review",
    },
    {
        "id": "kling",
        "name": "Kling AI",
        "kind": "hosted_free_tier",
        "capabilities": ["text_to_video", "image_to_video", "video_editing", "audio", "lip_sync"],
        "free_policy": "limited",
        "automation": "api_available_but_paid_resources",
        "official": "https://kling.ai/explore/kling_ai_faq",
        "watch": "https://kling.ai/",
        "brain_use": "optional_external_generation_after_cost_check",
    },
    {
        "id": "ltx_2",
        "name": "LTX-2",
        "kind": "open_source_self_hosted",
        "capabilities": ["text_to_video", "image_to_video", "audio_video", "keyframes", "video_to_video"],
        "free_policy": "self_hosted",
        "automation": "local_or_gpu_runner",
        "official": "https://github.com/Lightricks/LTX-Video",
        "watch": "https://github.com/Lightricks/LTX-Video/releases",
        "brain_use": "primary_candidate_for_self_hosted_video_backend",
    },
    {
        "id": "hunyuan_video",
        "name": "HunyuanVideo",
        "kind": "open_source_self_hosted",
        "capabilities": ["text_to_video"],
        "free_policy": "self_hosted",
        "automation": "local_or_gpu_runner",
        "official": "https://github.com/Tencent-Hunyuan/HunyuanVideo",
        "watch": "https://github.com/Tencent-Hunyuan/HunyuanVideo/releases",
        "brain_use": "research_backend_when_hardware_allows",
    },
    {
        "id": "runway",
        "name": "Runway",
        "kind": "hosted_free_tier",
        "capabilities": ["video_generation", "video_editing", "model_router"],
        "free_policy": "limited",
        "automation": "api_requires_credits",
        "official": "https://runway.com/",
        "watch": "https://runway.com/changelog",
        "brain_use": "watch_only_unless_free_credits_are_verified",
    },
]


def snapshot() -> dict:
    return {
        "policy": {
            "free_is_not_assumed_unlimited": True,
            "paid_api_is_never_selected_as_free": True,
            "self_hosted_is_hardware_limited": True,
        },
        "tools": TOOLS,
    }


def eligible_for_zero_cost_automation(tool: dict, *, self_hosted_runner: bool = False) -> bool:
    if tool["kind"] == "open_source_self_hosted":
        return self_hosted_runner
    return tool["free_policy"] == "unlimited"
