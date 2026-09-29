from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from PIL import Image
from cloud.flipbook_renderer import build_flipbook, render_frames

class FlipbookRendererTests(unittest.TestCase):
    def test_frames_are_numbered_and_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=render_frames(tmp,frames=6,width=320,height=240)
            self.assertEqual(len(paths),6)
            self.assertEqual(paths[0].name,"frame_0001.png")
            self.assertEqual(paths[-1].name,"frame_0006.png")
            with Image.open(paths[0]) as first, Image.open(paths[-1]) as last:
                self.assertNotEqual(first.tobytes(),last.tobytes())

    def test_end_to_end_mp4(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=build_flipbook(Path(tmp),frames=4,fps=8)
            self.assertTrue(result["verified"])
            self.assertEqual(result["frames"],4)
            self.assertTrue(Path(result["video"]).exists())

if __name__=="__main__": unittest.main()
