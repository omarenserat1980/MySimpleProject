from brain_v12.brain.cloud_hardware import (
    CPU, Memory, GPU, Storage, Network, Firmware, Management, Availability,
    HardwareManifest, WorkloadRequirement, build_virtual_motherboard,
    satisfies, select_executor,
)


def manifest(machine_id, threads=64, ram=256, gpu=0, vram=0, state="online"):
    return HardwareManifest(
        machine_id=machine_id,
        executor_class="gpu" if gpu else "cpu",
        state=state,
        source="observed",
        cpu=CPU("x86_64", 1, threads // 2, threads),
        memory=Memory(ram * 1024**3),
        gpu=GPU("test-gpu", gpu, vram * 1024**3),
        storage=Storage(2 * 1024**4),
        network=Network(100_000_000_000, rdma=True),
        firmware=Firmware(secure_boot=True, vtpm=True),
        management=Management(),
        availability=Availability(),
        metadata={"kvm": True},
    )


def test_reference_virtual_motherboard_validates():
    board = build_virtual_motherboard()
    board.validate()
    assert board.source == "declared"
    assert board.gpu.count == 8
    assert board.availability.zones == 3


def test_requirement_matches_capabilities():
    node = manifest("gpu-01", threads=128, ram=512, gpu=4, vram=384)
    req = WorkloadRequirement(cpu_threads=64, memory_bytes=128 * 1024**3,
                              gpu_count=2, gpu_vram_bytes=200 * 1024**3,
                              kvm=True, secure_boot=True, vtpm=True)
    assert satisfies(node, req)


def test_offline_executor_is_never_selected():
    node = manifest("dead", threads=256, ram=1024, gpu=8, vram=768, state="offline")
    req = WorkloadRequirement(gpu_count=1)
    assert not satisfies(node, req)
    assert select_executor([node], req) is None


def test_selection_is_deterministic():
    small = manifest("small", threads=64, ram=256, gpu=2, vram=192)
    large = manifest("large", threads=256, ram=1024, gpu=8, vram=768)
    req = WorkloadRequirement(cpu_threads=32, memory_bytes=64 * 1024**3, gpu_count=1)
    assert select_executor([large, small], req).machine_id == "small"


def test_invalid_gpu_manifest_is_rejected():
    node = manifest("bad")
    node.gpu = GPU("bad", 0, 1)
    try:
        node.validate()
        assert False, "expected validation failure"
    except ValueError:
        pass
