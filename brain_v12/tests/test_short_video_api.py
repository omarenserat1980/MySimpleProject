import unittest

from brain_v12.app import app


class ShortVideoApiTests(unittest.TestCase):
    def test_short_video_routes_exist(self):
        routes = {getattr(route, "path", "") for route in app.routes}
        self.assertIn("/api/short-video/health", routes)
        self.assertIn("/api/short-video/plan", routes)
        self.assertIn("/api/short-video/lipsync-command", routes)


if __name__ == "__main__":
    unittest.main()
