import unittest
from brain_v12.visual_engine import compile_scene, detect_mode, detect_palette, render_svg, scene_timeline

class VisualEngineTests(unittest.TestCase):
    def test_mode_detection(self):
        self.assertEqual(detect_mode("روبوت مستقبلي"), "robot")
        self.assertEqual(detect_mode("سيارة رياضية"), "car")
        self.assertEqual(detect_mode("مدينة مستقبلية"), "city")

    def test_palette_detection(self):
        self.assertEqual(detect_palette("منظر ليلي"), "night")
        self.assertEqual(detect_palette("غروب الشمس"), "sunset")

    def test_landscape_scene(self):
        scene=compile_scene("جبال وشجرة وبحيرة وبيت عند الغروب")
        self.assertEqual(scene["type"], "landscape")
        self.assertIn("mountains", scene["objects"])
        self.assertIn("lake", scene["objects"])
        self.assertIn("tree", scene["objects"])
        self.assertEqual(scene["palette"], "sunset")
        self.assertEqual(scene["version"], "1.1")
        self.assertTrue(scene["local"])

    def test_scene_timeline(self):
        scene=compile_scene("سيارة")
        timeline=scene_timeline(scene, 7)
        self.assertEqual(timeline["profile"], "youtube_1080p")
        self.assertEqual(timeline["scenes"][0]["duration"], 7)
        self.assertEqual(timeline["scenes"][0]["asset_type"], "svg")

    def test_svg_output(self):
        svg=render_svg(compile_scene("سيارة"))
        self.assertTrue(svg.startswith("<svg "))
        self.assertIn("<title>", svg)
        self.assertIn("<circle", svg)

if __name__=="__main__":
    unittest.main()
