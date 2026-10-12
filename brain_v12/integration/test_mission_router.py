from brain_v12.integration.mission_router import route

def test_commerce_finance_route():
    r=route("evaluate an Amazon product investment")
    assert "commerce" in r.specialists
    assert "finance" in r.specialists

def test_social_route():
    r=route("design a charity fundraising project")
    assert "social" in r.specialists
    assert "marketing" in r.specialists

def test_unknown_uses_intelligence():
    assert route("solve a new problem").specialists==("intelligence",)
