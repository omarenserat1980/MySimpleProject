import base64
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.draw_gateway import draw_local, draw_openai, parse_human_draw_request


class DrawGatewayTests(unittest.TestCase):
    def test_human_arabic_request_routes_local(self):
        x = parse_human_draw_request("Brain، ارسم لي مدينة مستقبلية ليلاً")
        self.assertTrue(x["ok"])
        self.assertEqual(x["intent"], "DRAW_IMAGE")
        self.assertEqual(x["provider"], "local")
        self.assertIn("مدينة", x["prompt"])

    def test_explicit_chatgpt_request_routes_openai(self):
        x = parse_human_draw_request("Brain، استدع ChatGPT وارسم لي قلعة")
        self.assertTrue(x["ok"])
        self.assertEqual(x["provider"], "openai")

    def test_local_draw_is_verified_svg(self):
        x = draw_local("بحيرة وجبل وشجرة عند الغروب")
        self.assertTrue(x["ok"])
        self.assertTrue(x["verified"])
        self.assertEqual(x["format"], "svg")
        self.assertIn("<svg", x["svg"])

    def test_openai_result_is_saved_and_verified(self):
        with tempfile.TemporaryDirectory() as td:
            raw = base64.b64encode(b"\x89PNG\r\n" + b"x" * 256).decode()
            x = draw_openai("قلعة", lambda prompt: {"ok": True, "b64_json": raw, "model": "test"}, Path(td))
            self.assertTrue(x["ok"])
            self.assertTrue(x["verified"])
            self.assertTrue((Path(td) / x["filename"]).is_file())


if __name__ == "__main__":
    unittest.main()
