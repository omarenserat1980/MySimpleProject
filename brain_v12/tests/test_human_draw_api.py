import unittest

from brain_v12.app import app


class HumanDrawApiTests(unittest.TestCase):
    def test_human_draw_route_exists(self):
        routes = {getattr(route, "path", "") for route in app.routes}
        self.assertIn("/api/draw", routes)

    def test_ai_status_route_exists(self):
        routes = {getattr(route, "path", "") for route in app.routes}
        self.assertIn("/api/ai/status", routes)


if __name__ == "__main__":
    unittest.main()
