from brain_v7.braincore_v2.capability_graph import graph_status,next_high_leverage

def test_dependency_frontier():
    s=graph_status({"software_tests","data_validation","research"})
    rows={x["name"]:x for x in s["capabilities"]}
    assert rows["opportunity_discovery"]["status"]=="READY"
    assert rows["lead_to_payment"]["status"]=="BLOCKED"

def test_high_leverage_is_dependency_aware():
    x=next_high_leverage({"software_tests","data_validation","research"})
    assert x["name"]=="opportunity_discovery"
