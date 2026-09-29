import pathlib
import unittest

class VisualMediaBridgeTests(unittest.TestCase):
    def test_media_engine_has_visual_bridge(self):
        path=pathlib.Path(__file__).resolve().parents[1]/"web"/"media-engine.html"
        content=path.read_text(encoding="utf-8")
        for marker in ("visualBridge","brain.visual.scene","importVisualScene","useVisualTimeline","loadVisualBridge"):
            self.assertIn(marker,content)

if __name__=="__main__":
    unittest.main()
