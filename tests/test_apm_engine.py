from __future__ import annotations
import json
import sys
from pathlib import Path
from brain_v12.apm.engine import APMEngine, load_pipeline, topo_order, verify_evidence

def write_pipeline(path: Path) -> None:
    pipeline = {
        "schema_version": "apm-pipeline/v1",
        "pipeline_id": "test-pipeline",
        "stages": [
            {"id": "01", "name": "one",
             "run": {"command": [sys.executable, "-c", "print('run1')"]},
             "verify": {"command": [sys.executable, "-c", "print('verify1')"]}},
            {"id": "02", "name": "two", "dependencies": ["01"],
             "run": {"command": [sys.executable, "-c", "print('run2')"]},
             "verify": {"command": [sys.executable, "-c", "print('verify2')"]}}
        ],
        "final_verify": {"command": [sys.executable, "-c", "print('final')"]}
    }
    path.write_text(json.dumps(pipeline), encoding="utf-8")

def test_dynamic_pipeline_and_evidence(tmp_path: Path) -> None:
    pipeline, state = tmp_path / "pipeline.json", tmp_path / "state"
    write_pipeline(pipeline)
    _, stages, _ = load_pipeline(pipeline)
    assert [x.id for x in topo_order(stages)] == ["01", "02"]
    result = APMEngine(pipeline, state, commit_sha="test-sha").run()
    assert result["status"] == "PASS"
    assert result["completed_stages"] == ["01", "02"]
    assert verify_evidence(state)["status"] == "PASS"

def test_resume_skips_completed_stage(tmp_path: Path) -> None:
    pipeline, state = tmp_path / "pipeline.json", tmp_path / "state"
    write_pipeline(pipeline)
    first = APMEngine(pipeline, state, commit_sha="test-sha").run()
    second = APMEngine(pipeline, state, commit_sha="test-sha").run()
    assert first["status"] == second["status"] == "PASS"
