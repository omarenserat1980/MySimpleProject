import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from brain_v12.brain.youtube_publisher import YouTubePublisher

class Store:
    def __init__(self): self.events=[]
    def event(self,name,payload): self.events.append((name,payload))

class PublisherGateTests(unittest.TestCase):
    def test_upload_never_reached_without_master_release(self):
        store=Store(); p=YouTubePublisher(store,credentials_provider=lambda: object())
        with tempfile.TemporaryDirectory() as d:
            media=Path(d)/"x.mp4"; media.write_bytes(b"not-video")
            with patch.object(p,"validate_release",return_value={"ok":True}), patch("brain_v12.brain.youtube_publisher.build") as build:
                result=p.publish_cinematic_release("Film",media_path=str(media),release_evidence=None)
        self.assertFalse(result["ok"]); self.assertTrue(result["release_blocked"]); build.assert_not_called()
        self.assertTrue(any(e[0]=="YOUTUBE_MASTER_RELEASE_BLOCKED" for e in store.events))

    def test_valid_release_reaches_oauth_stage(self):
        store=Store(); p=YouTubePublisher(store,credentials_provider=lambda: object())
        evidence={"film_id":"F1","film_version":"v1","production_run":"R1","artifact_sha256":"a"*64}
        for k in ("technical","cinematic","rights","legal_policy"):
            evidence[k]={"passed":True,"evidence_ref":f"F1/v1/R1/{k}/qc","evidence_sha256":"b"*64,"reviewed_artifact_sha256":"a"*64}
        with patch.object(p,"validate_release",return_value={"ok":True}), patch("brain_v12.brain.youtube_publisher.build") as build:
            result=p.publish_cinematic_release("Film",media_path="x.mp4",release_evidence=evidence)
        self.assertEqual(result["status"],"UPLOAD_FAILED"); build.assert_called_once()

if __name__=="__main__": unittest.main()
