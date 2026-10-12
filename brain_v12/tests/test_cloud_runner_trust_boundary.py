from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cloud_image_does_not_self_assert_trusted_runner_identity():
    dockerfile = (REPO_ROOT / "Dockerfile.brain-cloud").read_text(encoding="utf-8")
    assert "ENV BRAIN_INTERNAL_RUNNER_FLAG=1" not in dockerfile


def test_compose_does_not_self_assert_trusted_runner_identity():
    compose = (REPO_ROOT / "docker-compose.brain-cloud.yml").read_text(encoding="utf-8")
    assert 'BRAIN_INTERNAL_RUNNER_FLAG: "1"' not in compose
