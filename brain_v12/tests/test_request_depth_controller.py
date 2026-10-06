from brain_v12.self_healing.request_depth_controller import RequestDepthController

def test_depth_grows_per_request_and_capability_is_demand_driven(tmp_path):
    c = RequestDepthController(tmp_path / "depth.json")
    a = c.decide("اكتب سكربت لفحص Azure")
    assert a.depth == 1
    assert "script" in a.create_capabilities
    c.commit("اكتب سكربت لفحص Azure", a)

    b = c.decide("حل المشكلة الحالية")
    assert b.depth == 2
    assert "diagnostics" in b.create_capabilities

def test_no_unused_capabilities_are_created(tmp_path):
    c = RequestDepthController(tmp_path / "depth.json")
    d = c.decide("نفذ طلب بسيط")
    assert d.create_capabilities == ()
