import pathlib
import unittest

class TextToDrawingTests(unittest.TestCase):
    def test_visual_engine_page_contains_local_pipeline(self):
        path=pathlib.Path(__file__).resolve().parents[1]/"web"/"text-to-drawing"/"index.html"
        content=path.read_text(encoding="utf-8")
        for marker in ("BRAIN Visual Engine","/api/visual-engine/compile","downloadHTML","downloadSVG","downloadPNG"):
            self.assertIn(marker,content)
        self.assertNotIn("openai.com",content.lower())

    def test_visual_engine_backend_exists(self):
        path=pathlib.Path(__file__).resolve().parents[1]/"visual_engine.py"
        content=path.read_text(encoding="utf-8")
        self.assertIn("def compile_scene",content)
        self.assertIn("def render_svg",content)

if __name__=="__main__":
    unittest.main()
