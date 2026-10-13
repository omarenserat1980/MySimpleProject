from __future__ import annotations

from cloud.film_reliability import FilmReliabilityEngine


def test_film_renderer_fails_closed_without_v12_native_renderer(tmp_path):
    engine = FilmReliabilityEngine(tmp_path / "film", max_attempts=1)
    result = engine.run({"title": "contract-proof", "target_minutes": 1})

    assert result["ok"] is False
    assert result["error"] == "BRAIN_V12_RENDERER_NOT_INTEGRATED"
    assert result["legacy_factory_invoked"] is False
    assert result["video_path"] is None
    assert not (tmp_path / "film" / "final.mp4").exists()
    assert not (tmp_path / "film" / "film_manifest.json").exists()
    assert "BRAIN_V12_RENDERER_NOT_INTEGRATED" in (tmp_path / "film" / "reliability.log").read_text()
