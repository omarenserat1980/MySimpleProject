import pathlib
import unittest

class VideoPlayerTests(unittest.TestCase):
    def test_player_accepts_remote_source(self):
        path=pathlib.Path(__file__).resolve().parents[1]/"web"/"video-player"/"index.html"
        content=path.read_text(encoding="utf-8")
        for marker in ("function addRemote(url)", "URLSearchParams(location.search)", "video-player"):
            self.assertIn(marker,content)

if __name__=="__main__":
    unittest.main()
