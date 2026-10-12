from brain_v12.brain.workload_controller import WorkloadController

def test_emergency_blocks_background():
    c=WorkloadController()
    r=c.evaluate(queued=800,active=2,priority="BACKGROUND")
    assert not r["admit"] and r["reason"]=="CIRCUIT_BREAKER"

def test_critical_survives_emergency():
    assert WorkloadController().evaluate(queued=900,active=2,priority="CRITICAL")["admit"]

def test_duplicate_is_rejected():
    r=WorkloadController().evaluate(queued=10,active=1,key_active=1,duplicate=True)
    assert r["reason"]=="DUPLICATE"

def test_congested_blocks_low():
    assert not WorkloadController().evaluate(queued=500,active=2,priority="LOW")["admit"]
