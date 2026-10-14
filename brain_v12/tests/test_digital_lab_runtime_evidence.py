from brain_v12.digital_lab.runtime_evidence import validate_manifest


def component(result="PASS", *, required=True, revision="abc123", exit_status=0, component_id="api"):
    return {
        "component_id": component_id,
        "domain": "api",
        "required": required,
        "result": result,
        "source_revision": revision,
        "check_id": "health-readiness",
        "reference": "https://example.invalid/run/1",
        "observed_utc": "2026-10-14T12:00:00Z",
        "exit_status": exit_status,
        "scope": "readiness endpoint returned healthy",
        "limitations": "Does not prove all dependent services are healthy",
    }


def manifest(*components, revision="abc123"):
    return {
        "schema_version": 1,
        "source_revision": revision,
        "generated_utc": "2026-10-14T12:01:00Z",
        "components": list(components),
    }


def test_all_required_pass_means_ready():
    errors, status, counts = validate_manifest(manifest(component(), component(component_id="worker")))
    assert errors == []
    assert status == "READY"
    assert counts["PASS"] == 2


def test_required_not_run_fails_closed_as_blocked():
    item = component("NOT_RUN", exit_status=None)
    errors, status, _ = validate_manifest(manifest(item))
    assert errors == []
    assert status == "BLOCKED"


def test_required_blocked_fails_closed():
    errors, status, _ = validate_manifest(manifest(component("BLOCKED", exit_status=None)))
    assert errors == []
    assert status == "BLOCKED"


def test_required_failure_sets_fail_gate():
    errors, status, _ = validate_manifest(manifest(component("FAIL", exit_status=1)))
    assert errors == []
    assert status == "FAIL"


def test_revision_mismatch_is_invalid():
    errors, status, _ = validate_manifest(manifest(component(revision="older-sha")))
    assert status == "INVALID"
    assert any("source_revision" in error for error in errors)


def test_pass_with_nonzero_exit_is_invalid():
    errors, status, _ = validate_manifest(manifest(component(exit_status=1)))
    assert status == "INVALID"
    assert any("PASS requires" in error for error in errors)


def test_optional_failure_does_not_block_required_pass():
    errors, status, _ = validate_manifest(
        manifest(component(), component("FAIL", required=False, exit_status=1, component_id="optional"))
    )
    assert errors == []
    assert status == "READY"


def test_duplicate_component_ids_are_invalid():
    errors, status, _ = validate_manifest(manifest(component(), component()))
    assert status == "INVALID"
    assert any("duplicate component_id" in error for error in errors)


def test_empty_manifest_is_invalid():
    errors, status, _ = validate_manifest(manifest())
    assert status == "INVALID"
    assert any("non-empty list" in error for error in errors)
