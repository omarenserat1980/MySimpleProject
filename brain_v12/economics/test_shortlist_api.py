from economics.shortlist_api import router


def test_shortlist_route_exists():
    paths = {route.path for route in router.routes}
    assert "/api/economics/shortlist" in paths


def test_shortlist_is_post_only():
    route = next(route for route in router.routes if route.path == "/api/economics/shortlist")
    assert route.methods == {"POST"}
