import threading

from platform_foundation.audit_chain import AuditChain


def test_audit_chain_is_safe_under_concurrent_append():
    audit = AuditChain()
    threads = [
        threading.Thread(target=lambda i=i: audit.record('parallel', {'worker': i}))
        for i in range(32)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    events = audit.events()
    assert len(events) == 32
    assert [event.sequence for event in events] == list(range(1, 33))
    assert audit.verify()