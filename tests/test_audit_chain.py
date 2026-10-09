from platform_foundation.audit_chain import AuditChain


def test_chain_is_valid_after_append() -> None:
    chain = AuditChain()
    chain.record("task_started", {"id": "a"})
    chain.record("task_succeeded", {"id": "a"})
    assert chain.verify()


def test_tampering_is_detected() -> None:
    chain = AuditChain()
    chain.record("task_started", {"id": "a"})
    chain.record("task_succeeded", {"id": "a"})
    chain._events[0].payload["id"] = "tampered"
    assert not chain.verify()


def test_sequence_links_are_checked() -> None:
    chain = AuditChain()
    chain.record("one", {})
    chain.record("two", {})
    chain._events[1] = chain._events[1].__class__(
        99,
        chain._events[1].timestamp,
        chain._events[1].event,
        chain._events[1].payload,
        chain._events[1].previous_hash,
        chain._events[1].event_hash,
    )
    assert not chain.verify()
