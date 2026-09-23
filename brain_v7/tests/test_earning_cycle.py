from brain_v7.braincore_v2.earning_cycle import Stage,next_stage

def test_cycle_requires_user_submission():
    r=next_stage(has_evidence=True,fit_ok=True,risk_ok=True,ready_for_submission=True,delivered=False,payment_verified=False,result_recorded=False)
    assert r.stage is Stage.USER_SUBMISSION and r.requires_user_action

def test_cycle_waits_for_payment_confirmation():
    r=next_stage(has_evidence=True,fit_ok=True,risk_ok=True,ready_for_submission=True,delivered=True,payment_verified=False,result_recorded=False)
    assert r.stage is Stage.PAYMENT_PENDING

def test_cycle_learns_only_after_verified_result():
    r=next_stage(has_evidence=True,fit_ok=True,risk_ok=True,ready_for_submission=True,delivered=True,payment_verified=True,result_recorded=True)
    assert r.stage is Stage.LEARN
