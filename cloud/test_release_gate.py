from pathlib import Path
from cloud.release_gate import ReleaseGate

def test_gate_blocks_ready_without_artifact(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path); Path("docs").mkdir(); Path("docs/film.json").write_text('{"status":{"render":"ready","video":"ready","audio":"ready","verification":"ready","web":"ready"},"video":"assets/missing.mp4"}')
 for x in ["COMMERCIAL_GOVERNANCE_SPEC.md","PAYMENT_POLICY.md","PUBLIC_IDENTITY_AND_LIMITED_LIABILITY_POLICY.md"]: Path(x).write_text("x")
 assert ReleaseGate(tmp_path)._cinema_truth().passed is False
