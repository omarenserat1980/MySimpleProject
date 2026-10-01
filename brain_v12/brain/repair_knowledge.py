from __future__ import annotations

"""Allowlisted failure knowledge for Brain Supervisor recovery.

This module only describes diagnostics and bounded actions. It does not edit
source code or execute external commands by itself.
"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RepairKnowledge:
    rule_id: str
    classification: str
    patterns: tuple[str, ...]
    action: str
    safe_automatic: bool
    verification: tuple[str, ...]
    notes: str


RULES: tuple[RepairKnowledge, ...] = (
    RepairKnowledge(
        "FFMPEG_MISSING_INPUT",
        "MEDIA_OR_VM_PIPELINE",
        (r"No such file or directory", r"(ffmpeg|concat|input)"),
        "REBUILD_OR_RESELECT_INPUT_ARTIFACT",
        True,
        ("input_exists", "ffprobe_input", "final_qc"),
        "Do not invent a media path; resolve only from the task manifest/artifact store.",
    ),
    RepairKnowledge(
        "FFMPEG_INVALID_CODEC",
        "MEDIA_OR_VM_PIPELINE",
        (r"(Unknown encoder|Encoder .* not found|Invalid argument)", r"ffmpeg"),
        "SELECT_KNOWN_SUPPORTED_CODEC_OR_FALLBACK_PROFILE",
        True,
        ("ffmpeg_version", "short_render", "ffprobe_codec"),
        "Use an allowlisted profile; never silently lower the requested quality contract.",
    ),
    RepairKnowledge(
        "FFPROBE_NO_STREAM",
        "MEDIA_OR_VM_PIPELINE",
        (r"(Invalid data found when processing input|No streams|codec_type)", r"ffprobe"),
        "REJECT_ARTIFACT_AND_REBUILD",
        True,
        ("artifact_exists", "ffprobe_video_stream", "ffprobe_audio_stream"),
        "A missing required stream is a verification failure, not success.",
    ),
    RepairKnowledge(
        "FFMPEG_CONCAT_FAILURE",
        "MEDIA_OR_VM_PIPELINE",
        (r"(concat|Impossible to open|Unsafe file name)", r"ffmpeg"),
        "REBUILD_CONCAT_MANIFEST_AND_RETRY",
        True,
        ("manifest_order", "all_parts_exist", "concat_smoke", "master_qc"),
        "Only use the manifest as the source of truth for part ordering.",
    ),
    RepairKnowledge(
        "QEMU_MISSING",
        "EXECUTION_INFRA",
        (r"(qemu-system|command not found|No such file)",),
        "SELECT_AVAILABLE_VM_BACKEND_OR_BLOCK",
        False,
        ("qemu_version", "backend_capabilities"),
        "Never claim a Windows guest boot without an actual guest evidence record.",
    ),
    RepairKnowledge(
        "QEMU_TIMEOUT",
        "EXECUTION_INFRA",
        (r"(qemu|timeout|timed out)",),
        "RETRY_WITH_BOUNDED_TIMEOUT_OR_SELECT_FALLBACK_BACKEND",
        True,
        ("backend_available", "guest_boot_evidence", "completion_gate"),
        "A QEMU exit code alone is never proof of guest boot.",
    ),
    RepairKnowledge(
        "WINDOWS_MEDIA_INDEX",
        "INPUT_OR_ARTIFACT",
        (r"(install\.wim|install\.esd|image index|Index:)", r"(Windows Server 2025|DISM|wimlib)"),
        "DISCOVER_IMAGE_INDEX_FROM_MEDIA_METADATA",
        True,
        ("wim_metadata", "selected_index", "image_identity"),
        "Never hard-code an image index when the downloaded media can expose its metadata.",
    ),
    RepairKnowledge(
        "WINDOWS_GUEST_NOT_VERIFIED",
        "VERIFICATION_FATAL",
        (r"(WINDOWS_BOOT_VERIFIED|guest boot|completion gate)", r"(false|missing|rejected)"),
        "BLOCK_DELIVERY_AND_COLLECT_GUEST_EVIDENCE",
        False,
        ("windows_boot_evidence", "network_evidence", "storage_evidence", "completion_gate"),
        "Do not convert infrastructure success into Windows boot success.",
    ),
    RepairKnowledge(
        "ARTIFACT_MISSING",
        "INPUT_OR_ARTIFACT",
        (r"(artifact.*not found|No such file|cannot open)",),
        "REBUILD_ARTIFACT_FROM_MANIFEST",
        True,
        ("manifest_exists", "artifact_exists", "sha256", "final_qc"),
        "Only rebuild artifacts whose recipe is deterministic and recorded.",
    ),
    RepairKnowledge(
        "UNKNOWN_FAILURE",
        "UNKNOWN",
        (r".*",),
        "BLOCK_FOR_REVIEW",
        False,
        ("capture_logs", "preserve_artifacts", "classify_again"),
        "Unknown failures must not trigger source mutation.",
    ),
)


def match_rules(log: str) -> list[RepairKnowledge]:
    text = str(log or "")
    return [
        rule
        for rule in RULES
        if all(re.search(pattern, text, re.IGNORECASE) for pattern in rule.patterns)
    ]


def classify(log: str) -> RepairKnowledge:
    matches = match_rules(log)
    return matches[0] if matches else RULES[-1]
