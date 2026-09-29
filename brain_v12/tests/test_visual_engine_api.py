import unittest
from brain_v12.app import app
from brain_v12 import visual_engine

class VisualEngineApiContractTests(unittest.TestCase):
    def test_scene_compiler_contract(self):
        scene=visual_engine.compile_scene("مدينة ليلية مع برج")
        self.assertEqual(scene["type"], "city")
        self.assertEqual(scene["palette"], "night")
        self.assertIn("tower", scene["objects"])

    def test_media_visual_scene_route_exists(self):
        routes={getattr(r,"path","") for r in app.routes}
        self.assertIn("/api/media/visual-scene", routes)
        self.assertIn("/api/visual-engine/compile", routes)

if __name__=="__main__":
    unittest.main()
