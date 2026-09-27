import tempfile
from pathlib import Path
from cinematic_image_engine_v51.orchestrator import ImageFactory

def test_resume_and_planning():
    with tempfile.TemporaryDirectory() as d:
        f=ImageFactory(d); s=f.initialize("TEST")
        shots=f.prepare(s,"ROOFTOP\nHero waits\n\nSTREET\nHero walks")
        assert len(shots)==6
        assert (Path(d)/"project_state.json").exists()
