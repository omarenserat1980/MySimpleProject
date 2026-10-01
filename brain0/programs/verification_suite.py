"""Dependency-free verification suite for BRAIN-0/1."""
import os
import tempfile

from brain0.core import LOAD, ADD, VERIFY, HALT, encode, BrainVM
from brain0.runtime import BrainRuntime
from brain0.memory import Memory
from brain0.termux_adapter import accept_task


def main():
    p = b"".join(
        [
            encode(LOAD, 1, 7, 0),
            encode(LOAD, 2, 5, 0),
            encode(ADD, 1, 2, 0),
            encode(VERIFY, 1, 12, 0),
            encode(HALT),
        ]
    )

    vm = BrainVM()
    vm.load(p)
    r = vm.run(max_steps=1000)
    assert r["status"] == "VERIFIED_COMPLETED"
    assert r["registers"][1] == 12

    with tempfile.TemporaryDirectory() as td:
        memory_path = os.path.join(td, "memory.json")
        rt = BrainRuntime(memory_path=memory_path)
        rr = rt.run("suite-001", p)
        assert rr["status"] == "VERIFIED_COMPLETED"
        assert rr["evidence_chain_valid"] is True
        assert rr["memory"]["values"]["last_status"] == "VERIFIED_COMPLETED"

        restored = Memory(path=memory_path)
        assert restored.get("last_task") == "suite-001"
        assert restored.get("last_status") == "VERIFIED_COMPLETED"
        assert restored.version == rr["memory"]["version"]

    assert accept_task("status")["accepted"] is True
    try:
        accept_task("shell")
    except ValueError as e:
        assert str(e) == "TASK_NOT_ALLOWED"
    else:
        raise AssertionError("unsafe task was accepted")

    print("BRAIN-0/1 DEPENDENCY-FREE TEST SUITE: VERIFIED")
    print("BRAIN-0/1 PERSISTENT MEMORY: VERIFIED")


if __name__ == "__main__":
    main()
