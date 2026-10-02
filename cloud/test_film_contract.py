from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from cloud import film_reliability


def test_film_contract_reaches_verified_completed_with_real_ffprobe(tmp_path, monkeypatch):
    real_run = subprocess.run

    def fake_run(command, *args, **kwargs):
        if (
            len(command) >= 3
            and command[0] == sys.executable
            and command[1] == "-m"
            and command[2] == "brain_v7.braincore_v2.background_factory_worker"
        ):
            output = Path(kwargs["env"]["FACTORY_OUTPUT_DIR"]) / "final.mp4"
            ffmpeg = shutil.which("ffmpeg")
            assert ffmpeg, "ffmpeg is required for the film contract test"
            rendered = real_run(
                [
                    ffmpeg, "-y",
                    "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1",
                    "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
                    "-shortest", "-c:v", "libx264", "-c:a", "aac",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            return subprocess.CompletedProcess(command, rendered.returncode, rendered.stdout, rendered.stderr)
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(film_reliability.subprocess, "run", fake_run)

    engine = film_reliability.FilmReliabilityEngine(tmp_path / "film", max_attempts=1)
    result = engine.run({"title": "contract-proof", "target_minutes": 1})

    assert result["ok"] is True
    manifest = json.loads((tmp_path / "film" / "film_manifest.json").read_text())
    expected = ["QUEUED", "RUNNING", "RENDERED", "QC", "MASTER_QC", "VERIFIED_COMPLETED"]
    assert manifest["stage_contract"] == expected
    assert manifest["status"] == "VERIFIED_COMPLETED"
    assert manifest["attempt_history"][0]["stage_history"] == expected
    assert Path(result["video_path"]).is_file()
    assert Path(result["video_path"]).stat().st_size > 1024
