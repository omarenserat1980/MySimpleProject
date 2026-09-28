from pathlib import Path

from .cinematic_local_renderer import CinematicLocalRenderer


def test_local_renderer_filter_uses_time_not_frame_N():
    source = Path(__file__).with_name("cinematic_local_renderer.py").read_text(encoding="utf-8")
    assert "sin(N/" not in source
    assert "cos(N/" not in source
    assert "sin(t*24/96)" in source


def test_local_renderer_smoke(tmp_path):
    renderer = CinematicLocalRenderer(output_dir=str(tmp_path))
    result = renderer.render(
        shot={"shot_id": "TEST-SMOKE", "duration_s": 3, "action": "Cinematic smoke test"},
        authorized=True,
    )
    assert result["status"] == "VERIFIED_COMPLETED", result
    assert result["local_visual_qc"]["status"] == "PASS", result
    assert Path(result["video_ref"]).is_file()
