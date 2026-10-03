from pathlib import Path
from cloud.release_gate import ReleaseGate

def test_gate_blocks_ready_without_artifact(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path); Path("docs").mkdir(); Path("docs/film.json").write_text('{"status":{"render":"ready","video":"ready","audio":"ready","verification":"ready","web":"ready"},"video":"assets/missing.mp4"}')
 for x in ["COMMERCIAL_GOVERNANCE_SPEC.md","PAYMENT_POLICY.md","PUBLIC_IDENTITY_AND_LIMITED_LIABILITY_POLICY.md"]: Path(x).write_text("x")
 assert ReleaseGate(tmp_path)._cinema_truth().passed is False


def test_probe_media_uses_brain_ffprobe_and_records_path(tmp_path,monkeypatch):
 from types import SimpleNamespace
 from brain_v12 import brain_ffmpeg
 import cloud.release_gate as release_gate

 calls=[]
 monkeypatch.setattr(brain_ffmpeg,"ffprobe",lambda:"/brain/bin/ffprobe")
 def fake_run(command,**kwargs):
  calls.append(command)
  return SimpleNamespace(returncode=0,stderr="",stdout='{"format":{"duration":"2.5"},"streams":[{"codec_type":"video","width":1280,"height":720},{"codec_type":"audio"}]}')
 monkeypatch.setattr(release_gate.subprocess,"run",fake_run)

 probe=ReleaseGate(tmp_path)._probe_media(tmp_path/"clip.mp4")

 assert calls[0][0]=="/brain/bin/ffprobe"
 assert probe["ffprobe_path"]=="/brain/bin/ffprobe"
 assert probe["duration"]==2.5
 assert probe["video"] and probe["audio"]
