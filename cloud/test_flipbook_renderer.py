from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from PIL import Image
from cloud.flipbook_renderer import build_flipbook, render_pages_from_images, render_frames

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

def test_external_drawing_pages(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for index in range(1, 4):
        image = Image.new("RGB", (160, 90), "white")
        image.save(source_dir / f"drawing_{index}.png")
    pages = render_pages_from_images(
        [source_dir / "drawing_1.png", source_dir / "drawing_2.png", source_dir / "drawing_3.png"],
        tmp_path / "pages",
    )
    assert [p.name for p in pages] == ["frame_0001.png", "frame_0002.png", "frame_0003.png"]
