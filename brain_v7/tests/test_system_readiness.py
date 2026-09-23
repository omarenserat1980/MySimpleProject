from brain_v7.braincore_v2.system_readiness import Readiness

def test_unknown_money_blocks_execution():
    r=Readiness(True,True,True,True,False,False)
    assert not r.executable and "real_funds_known" in r.blockers()

def test_side_effects_flag_is_never_executable():
    r=Readiness(True,True,True,True,True,True)
    assert not r.executable
