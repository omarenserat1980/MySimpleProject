from cloud.brain_node_security import create_enrollment, verify_enrollment, consume_enrollment

def test_enrollment_token_is_single_use(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path))
    issued=create_enrollment("node-1", ttl_seconds=300)
    assert verify_enrollment("node-1", issued["enrollment_token"])
    assert consume_enrollment("node-1", issued["enrollment_token"])
    assert not verify_enrollment("node-1", issued["enrollment_token"])
    assert not consume_enrollment("node-1", "wrong-token")
