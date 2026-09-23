from brain_v7.braincore_v2.deployment_readiness import inspect_environment, inspect_factory_config


def test_runtime_environment_requires_core_settings():
    report = inspect_environment({"BRAIN_SLEEP_SECONDS": "60", "FACTORY_INTERVAL_SECONDS": "21600"})
    assert report["runtime_configured"] is True


def test_factory_authorization_is_distinct_from_success():
    report = inspect_factory_config({
        "FACTORY_ALLOW_PRODUCTION": "1",
        "FACTORY_ALLOW_YOUTUBE_PUBLISH": "1",
    })
    assert report["production_authorized"] is True
    assert report["youtube_publish_authorized"] is True
    assert report["authorization_is_not_proof_of_success"] is True
