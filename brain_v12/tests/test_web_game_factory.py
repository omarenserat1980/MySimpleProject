from brain_v12.business.web_game_factory import WebGameFactory

def test_web_game_build_has_entrypoint_and_digest():
    doc, release = WebGameFactory().build("GAME-BRAIN-RUNNER","Brain Runner")
    assert "<!doctype html>" in doc
    assert release.entrypoint == "index.html"
    assert len(release.sha256) == 64
    assert release.status == "BUILT"

def test_game_title_is_escaped():
    doc, _ = WebGameFactory().build("GAME-X","A < B")
    assert "A &lt; B" in doc
