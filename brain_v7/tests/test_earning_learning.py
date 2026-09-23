from brain_v7.braincore_v2.earning_learning import Outcome,accept_outcome

def test_unverified_payment_is_not_profit():
    assert accept_outcome(Outcome("x",100,False,""))["profit_jod"]==0

def test_verified_payment_becomes_recordable_profit():
    r=accept_outcome(Outcome("x",100,True,"provider:P1"))
    assert r["accepted"] and r["profit_jod"]==100
