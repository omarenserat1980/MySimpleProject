from brain_v12.self_healing.problem_completion_gate import CompletionContract, ProblemCompletionGate, CompletionState

def test_execution_is_not_completion():
    g=ProblemCompletionGate(CompletionContract({"service":"READY"}))
    r=g.decision({"service":"STARTED"},{"verified":True})
    assert r["action"]=="treat"
    assert g.state==CompletionState.TREATMENT_REQUIRED
    assert g.diagnostic_depth==0

def test_completion_requires_world_state_and_evidence():
    g=ProblemCompletionGate(CompletionContract({"service":"READY"},{"regression":False}))
    r=g.decision({"service":"READY","regression":False},{"verified":True})
    assert r["action"]=="deliver"
    assert g.state==CompletionState.VERIFIED_COMPLETED
