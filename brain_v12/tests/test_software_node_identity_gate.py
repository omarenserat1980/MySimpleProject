import hashlib

from brain_v12.brain.software_node_identity_gate import SoftwareNodeIdentityGate, sign_node_response


def test_fresh_challenge_and_task_result_verify_as_software_node_only():
    now = [1_800_000_000]
    secret = b"test-secret-provisioned-out-of-band"
    gate = SoftwareNodeIdentityGate({"worker-1": secret}, clock=lambda: now[0], nonce_factory=lambda: "fresh-nonce-1")
    challenge = gate.issue_challenge("worker-1")
    result_hash = hashlib.sha256(b"safe test result").hexdigest()
    signature = sign_node_response(secret, node_id="worker-1", nonce=challenge["nonce"],
                                   issued_at=challenge["issued_at"], task_id="task-123", result_sha256=result_hash)
    result = gate.verify_response(node_id="worker-1", nonce=challenge["nonce"], issued_at=challenge["issued_at"],
                                  task_id="task-123", result_sha256=result_hash, signature=signature)
    assert result["status"] == "SOFTWARE_NODE_VERIFIED"
    assert result["physical_hardware_verified"] is False
    assert result["independent_host_attestation_verified"] is False


def test_unknown_node_cannot_get_challenge():
    gate = SoftwareNodeIdentityGate({})
    try:
        gate.issue_challenge("unregistered")
        assert False, "expected identity configuration failure"
    except PermissionError as exc:
        assert str(exc) == "NODE_IDENTITY_NOT_CONFIGURED"


def test_wrong_secret_is_rejected():
    now = [1_800_000_000]
    gate = SoftwareNodeIdentityGate({"worker-1": b"trusted-secret"}, clock=lambda: now[0], nonce_factory=lambda: "nonce-2")
    challenge = gate.issue_challenge("worker-1")
    result_hash = hashlib.sha256(b"result").hexdigest()
    signature = sign_node_response(b"attacker-secret", node_id="worker-1", nonce=challenge["nonce"],
                                   issued_at=challenge["issued_at"], task_id="task-1", result_sha256=result_hash)
    result = gate.verify_response(node_id="worker-1", nonce=challenge["nonce"], issued_at=challenge["issued_at"],
                                  task_id="task-1", result_sha256=result_hash, signature=signature)
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "IDENTITY_PROOF_INVALID"


def test_challenge_cannot_be_replayed():
    now = [1_800_000_000]
    secret = b"trusted-secret"
    gate = SoftwareNodeIdentityGate({"worker-1": secret}, clock=lambda: now[0], nonce_factory=lambda: "nonce-3")
    challenge = gate.issue_challenge("worker-1")
    result_hash = hashlib.sha256(b"result").hexdigest()
    signature = sign_node_response(secret, node_id="worker-1", nonce=challenge["nonce"],
                                   issued_at=challenge["issued_at"], task_id="task-1", result_sha256=result_hash)
    args = dict(node_id="worker-1", nonce=challenge["nonce"], issued_at=challenge["issued_at"],
                task_id="task-1", result_sha256=result_hash, signature=signature)
    assert gate.verify_response(**args)["status"] == "SOFTWARE_NODE_VERIFIED"
    replay = gate.verify_response(**args)
    assert replay["status"] == "BLOCKED"
    assert replay["reason"] == "CHALLENGE_UNKNOWN_OR_REPLAYED"


def test_expired_challenge_is_rejected():
    now = [1_800_000_000]
    secret = b"trusted-secret"
    gate = SoftwareNodeIdentityGate({"worker-1": secret}, ttl_seconds=5, clock=lambda: now[0], nonce_factory=lambda: "nonce-4")
    challenge = gate.issue_challenge("worker-1")
    now[0] += 6
    result_hash = hashlib.sha256(b"result").hexdigest()
    signature = sign_node_response(secret, node_id="worker-1", nonce=challenge["nonce"],
                                   issued_at=challenge["issued_at"], task_id="task-1", result_sha256=result_hash)
    result = gate.verify_response(node_id="worker-1", nonce=challenge["nonce"], issued_at=challenge["issued_at"],
                                  task_id="task-1", result_sha256=result_hash, signature=signature)
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "CHALLENGE_EXPIRED"


def test_challenge_is_expired_at_exact_expiry_boundary():
    now = [1_800_000_000]
    secret = b"trusted-secret"
    gate = SoftwareNodeIdentityGate({"worker-1": secret}, ttl_seconds=5, clock=lambda: now[0], nonce_factory=lambda: "nonce-exact-expiry")
    challenge = gate.issue_challenge("worker-1")
    now[0] = challenge["expires_at"]
    result_hash = hashlib.sha256(b"result").hexdigest()
    signature = sign_node_response(secret, node_id="worker-1", nonce=challenge["nonce"],
                                   issued_at=challenge["issued_at"], task_id="task-1", result_sha256=result_hash)
    result = gate.verify_response(node_id="worker-1", nonce=challenge["nonce"], issued_at=challenge["issued_at"],
                                  task_id="task-1", result_sha256=result_hash, signature=signature)
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "CHALLENGE_EXPIRED"
