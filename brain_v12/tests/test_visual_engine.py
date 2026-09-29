import unittest
from brain_v12.visual_engine import compile_scene, detect_mode, render_svg

class VisualEngineTests(unittest.TestCase):
    def test_mode_detection(self):
        self.assertEqual(detect_mode("روبوت مستقبلي"), "robot")
        self.assertEqual(detect_mode("سيارة رياضية"), "car")
        self.assertEqual(detect_mode("مدينة مستقبلية"), "city")

    def test_landscape_scene(self):
        scene=compile_scene("جبال وشجرة وبحيرة وبيت")
        self.assertEqual(scene["type"], "landscape")
        self.assertIn("mountains", scene["objects"])
        self.assertIn("lake", scene["objects"])
        self.assertTrue(scene["local"])

    def test_svg_output(self):
        svg=render_svg(compile_scene("سيارة"))
        self.assertTrue(svg.startswith("<svg "))
        self.assertIn("<title>", svg)
        self.assertIn("<circle", svg)

if __name__=="__main__":
    unittest.main()
