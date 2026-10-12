"""Brain-owned default capability catalog.

Declarative only: registration never claims runtime health or successful output.
Adapters must be probed before activation and verification must approve outputs.
"""
from __future__ import annotations

from .capability_fabric import CapabilityFabric, ExecutorSpec

DEFAULT_EXECUTORS: tuple[ExecutorSpec, ...] = (
    ExecutorSpec("local-ffmpeg", "media.render", priority=10, cost_class="FREE",
                 metadata={"kind": "brain_owned", "adapter": "ffmpeg", "tier": "BRAIN_OWNED", "requires_probe": True}),
    ExecutorSpec("local-pillow", "media.image", priority=10, cost_class="FREE",
                 metadata={"kind": "brain_owned", "adapter": "pillow", "tier": "BRAIN_OWNED", "requires_probe": True}),
    ExecutorSpec("comfyui-local", "media.video_generation", priority=20, cost_class="FREE",
                 metadata={"kind": "brain_owned", "adapter": "ComfyUIVideoAdapter", "tier": "BRAIN_OWNED", "requires_probe": True}),
    ExecutorSpec("brain-ai-gateway", "ai.reasoning", priority=30, cost_class="FREE",
                 metadata={"kind": "brain_owned", "adapter": "AIGateway", "tier": "BRAIN_OWNED", "provider_neutral": True}),
    ExecutorSpec("brain-code-agent", "code.execute", priority=20, cost_class="FREE",
                 metadata={"kind": "brain_owned", "adapter": "developer-agent", "tier": "BRAIN_OWNED"}),
    ExecutorSpec("brain-device-bridge", "device.execute", priority=20, cost_class="FREE",
                 permissions=frozenset({"device"}),
                 metadata={"kind": "brain_owned", "adapter": "DeviceBridge", "tier": "BRAIN_OWNED"}),
    ExecutorSpec("youtube-publisher", "publish.youtube", priority=50, cost_class="FREE",
                 permissions=frozenset({"external_publish", "youtube.upload"}),
                 metadata={"kind": "external", "adapter": "youtube_publisher", "tier": "FREE_DIVERSE", "side_effect": True}),
)

def build_default_fabric(*, include_offline: bool = False) -> CapabilityFabric:
    fabric = CapabilityFabric()
    for spec in DEFAULT_EXECUTORS:
        if include_offline or not spec.metadata.get("requires_probe"):
            fabric.register(spec)
    return fabric

def catalog_snapshot() -> list[dict]:
    return [
        {"executor_id": s.executor_id, "capability": s.capability,
         "priority": s.priority, "cost_class": s.cost_class,
         "permissions": sorted(s.permissions), "metadata": dict(s.metadata)}
        for s in DEFAULT_EXECUTORS
    ]
