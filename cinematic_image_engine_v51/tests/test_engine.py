import tempfile
from pathlib import Path
from cinematic_image_engine_v51.orchestrator import ImageFactory

def test_resume_and_planning():
    with tempfile.TemporaryDirectory() as d:
        f=ImageFactory(d); s=f.initialize("TEST")
        shots=f.prepare(s,"ROOFTOP\nHero waits\n\nSTREET\nHero walks")
        assert len(shots)==6
        assert (Path(d)/"project_state.json").exists()

def test_verified_shot_is_skipped():
    with tempfile.TemporaryDirectory() as d:
        f=ImageFactory(d); s=f.initialize("TEST")
        shots=f.prepare(s,"ROOFTOP\nHero waits")
        sid=shots[0].shot_id
        s.shots[sid]["status"]="VERIFIED"
        s.shots[sid]["master_file"]=str(Path(d)/"master"/"x.png")
        assert f.state_mgr.verified(s,sid) is True
        assert f.state_mgr.first_unverified(s,[sid,shots[1].shot_id]) == shots[1].shot_id
