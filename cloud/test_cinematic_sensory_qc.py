from cloud.cinematic_sensory_qc import CinematicSensoryQC

def test_shot_inspection_records_both_modalities():
    qc = CinematicSensoryQC()
    result = qc.inspect_shot(
        "S01",
        visual="hospital corridor",
        audio="rain and footsteps",
    )
    assert result["vision"]["modality"] == "vision"
    assert result["hearing"]["modality"] == "hearing"

def test_continuity_qc_detects_location_change():
    qc = CinematicSensoryQC()
    result = qc.continuity_check(
        {"character": "A", "location": "corridor", "time": "night", "audio_signature": "rain"},
        {"character": "A", "location": "room", "time": "night", "audio_signature": "rain"},
    )
    assert result["ok"] is False
    assert "location_continuity" in result["issues"]

def test_clean_continuity_passes():
    qc = CinematicSensoryQC()
    result = qc.continuity_check(
        {"character": "A", "location": "corridor", "time": "night", "audio_signature": "rain"},
        {"character": "A", "location": "corridor", "time": "night", "audio_signature": "rain"},
    )
    assert result["ok"] is True
