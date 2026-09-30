from brain_v12.brain.capability_router import candidates, route

def test_video_candidates():
    assert [x["id"] for x in candidates("video_generation")] == ["comfyui","ltx2"]

def test_route_does_not_assume_service():
    assert route("video_generation")["selected"] is None

def test_route_selects_available():
    assert route("video_generation", {"ltx2"})["selected"]["id"] == "ltx2"
