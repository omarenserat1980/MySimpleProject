"""Proof that Brain itself can govern a development task."""
from brain0.core import LOAD, ADD, VERIFY, HALT, encode
from brain0.self_developer import BrainNativeDeveloper


def main():
    program = b"".join([
        encode(LOAD, 1, 7, 0),
        encode(LOAD, 2, 5, 0),
        encode(ADD, 1, 2, 0),
        encode(VERIFY, 1, 12, 0),
        encode(HALT),
    ])

    brain = BrainNativeDeveloper()
    task = brain.plan("self-dev-001", "verify", "brain0")
    assert task.state == "PLANNED"

    brain.verify_capability("self-dev-001")
    assert brain.tasks["self-dev-001"].state == "VERIFIED"

    result = brain.run("self-dev-001", program)
    assert result["status"] == "VERIFIED_COMPLETED"
    assert result["evidence_chain_valid"] is True
    assert brain.tasks["self-dev-001"].state == "COMPLETED"

    try:
        brain.plan("unsafe", "shell", "anything")
    except ValueError as exc:
        assert str(exc) == "DEVELOPMENT_ACTION_NOT_ALLOWED"
    else:
        raise AssertionError("unsafe development action was accepted")

    print("BRAIN-NATIVE DEVELOPMENT LOOP: VERIFIED")


if __name__ == "__main__":
    main()
