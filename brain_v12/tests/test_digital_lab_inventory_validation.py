from brain_v12.digital_lab.validate_inventory import validate_inventory


def valid_report():
    return {
        "schema_version": 1,
        "inventory_type": "repository_path_metadata_only",
        "generated_utc": "2026-10-14T00:00:00+00:00",
        "repository_root": "/repo",
        "commit_sha": "abc123",
        "asset_count": 1,
        "coverage_limitations": ["repository files only"],
        "assets": [{
            "asset_id": "brain_v12/app.py",
            "path": "brain_v12/app.py",
            "domain": "code_or_script",
            "size_bytes": 10,
            "modified_utc": "2026-10-14T00:00:00+00:00",
            "lifecycle_status": "DISCOVERED_NOT_TESTED",
            "verification_status": "NOT_RUN",
            "evidence": [],
        }],
    }


def valid_evidence():
    return [{"source": "github_actions", "reference": "https://github.com/example/repo/actions/runs/1",
             "observed_utc": "2026-10-14T00:00:00Z", "result": "PASS"}]


def test_accepts_metadata_only_inventory():
    assert validate_inventory(valid_report()) == []


def test_rejects_asset_count_mismatch():
    report = valid_report()
    report["asset_count"] = 2
    assert any("asset_count" in error for error in validate_inventory(report))


def test_rejects_path_traversal():
    report = valid_report()
    report["assets"][0]["path"] = "../outside.txt"
    report["assets"][0]["asset_id"] = "../outside.txt"
    assert any("unsafe path" in error for error in validate_inventory(report))


def test_rejects_duplicate_paths():
    report = valid_report()
    report["assets"].append(dict(report["assets"][0]))
    report["asset_count"] = 2
    assert any("duplicate asset path" in error for error in validate_inventory(report))


def test_rejects_claimed_pass_for_untested_asset():
    report = valid_report()
    report["assets"][0]["verification_status"] = "PASS"
    assert any("cannot claim verification" in error for error in validate_inventory(report))


def test_rejects_pass_without_evidence():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "IN_REVIEW"
    report["assets"][0]["verification_status"] = "PASS"
    assert any("without evidence" in error for error in validate_inventory(report))


def test_accepts_verified_asset_with_evidence():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "ACCEPTED"
    report["assets"][0]["verification_status"] = "PASS"
    report["assets"][0]["evidence"] = valid_evidence()
    assert validate_inventory(report) == []


def test_rejects_accepted_asset_without_evidence():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "ACCEPTED"
    report["assets"][0]["verification_status"] = "PASS"
    assert any("cannot be ACCEPTED" in error for error in validate_inventory(report))


def test_rejects_malformed_evidence_record():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "IN_REVIEW"
    report["assets"][0]["verification_status"] = "PASS"
    report["assets"][0]["evidence"] = [{"source": "ci"}]
    errors = validate_inventory(report)
    assert any("missing fields" in error and "evidence" in error for error in errors)


def test_rejects_empty_coverage_limitations():
    report = valid_report()
    report["coverage_limitations"] = []
    assert any("coverage_limitations" in error for error in validate_inventory(report))
def test_accepts_testing_lifecycle_without_claiming_pass():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "TESTING"
    report["assets"][0]["verification_status"] = "NOT_RUN"
    assert validate_inventory(report) == []


def test_requires_blocked_verification_for_blocked_lifecycle():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "BLOCKED"
    assert any("cannot be BLOCKED" in error for error in validate_inventory(report))


def test_accepts_explicit_blocked_state_without_claiming_success():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "BLOCKED"
    report["assets"][0]["verification_status"] = "BLOCKED"
    assert validate_inventory(report) == []


def test_rejects_blocked_verification_in_testing_lifecycle():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "TESTING"
    report["assets"][0]["verification_status"] = "BLOCKED"
    assert any("requires BLOCKED or QUARANTINED" in error
               for error in validate_inventory(report))
