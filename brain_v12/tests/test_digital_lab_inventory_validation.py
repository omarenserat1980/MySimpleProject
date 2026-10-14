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
    return [{
        "source": "github_actions",
        "tool_version": "actions/checkout@v4 + Python 3.12",
        "source_revision": "abc123",
        "reference": "https://github.com/example/repo/actions/runs/1",
        "observed_utc": "2026-10-14T00:00:00Z",
        "result": "PASS",
        "check_id": "unit-tests",
        "exit_status": 0,
        "scope": "focused validator tests",
        "limitations": "does not prove runtime health",
    }]


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


def test_accepts_explicit_blocked_state_with_matching_evidence():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "BLOCKED"
    report["assets"][0]["verification_status"] = "BLOCKED"
    evidence = valid_evidence()[0]
    evidence["result"] = "BLOCKED"
    evidence["exit_status"] = 1
    report["assets"][0]["evidence"] = [evidence]
    assert validate_inventory(report) == []


def test_rejects_blocked_verification_in_testing_lifecycle():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "TESTING"
    report["assets"][0]["verification_status"] = "BLOCKED"
    assert any("requires BLOCKED or QUARANTINED" in error
               for error in validate_inventory(report))

def test_rejects_evidence_missing_tool_and_revision_identity():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "IN_REVIEW"
    report["assets"][0]["verification_status"] = "PASS"
    report["assets"][0]["evidence"] = [{"source": "ci", "reference": "run", "observed_utc": "now", "result": "PASS"}]
    errors = validate_inventory(report)
    assert any("tool_version" in error for error in errors)
    assert any("source_revision" in error for error in errors)


def test_rejects_partial_artifact_digest_metadata():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "IN_REVIEW"
    report["assets"][0]["verification_status"] = "PASS"
    evidence = valid_evidence()[0]
    evidence["artifact_path"] = "out/report.json"
    report["assets"][0]["evidence"] = [evidence]
    assert any("provide artifact_path" in error for error in validate_inventory(report))


def test_rejects_invalid_artifact_sha256():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "IN_REVIEW"
    report["assets"][0]["verification_status"] = "PASS"
    evidence = valid_evidence()[0]
    evidence.update({"artifact_path": "out/report.json", "artifact_size_bytes": 10, "artifact_sha256": "bad"})
    report["assets"][0]["evidence"] = [evidence]
    assert any("64-character hexadecimal SHA-256" in error for error in validate_inventory(report))

def test_rejects_pass_state_when_evidence_says_fail():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "IN_REVIEW"
    report["assets"][0]["verification_status"] = "PASS"
    evidence = valid_evidence()[0]
    evidence["result"] = "FAIL"
    evidence["exit_status"] = 1
    report["assets"][0]["evidence"] = [evidence]
    assert any("requires matching evidence result" in error for error in validate_inventory(report))


def test_rejects_blocked_state_without_blocked_evidence():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "BLOCKED"
    report["assets"][0]["verification_status"] = "BLOCKED"
    report["assets"][0]["evidence"] = valid_evidence()
    assert any("requires matching evidence result" in error for error in validate_inventory(report))

def test_rejects_non_string_evidence_result_without_crashing():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "IN_REVIEW"
    report["assets"][0]["verification_status"] = "PASS"
    evidence = valid_evidence()[0]
    evidence["result"] = ["PASS"]
    report["assets"][0]["evidence"] = [evidence]
    errors = validate_inventory(report)
    assert any(".result must be one of" in error for error in errors)


def test_rejects_evidence_from_stale_source_revision():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "ACCEPTED"
    report["assets"][0]["verification_status"] = "PASS"
    evidence = valid_evidence()
    evidence[0]["source_revision"] = "older-commit"
    report["assets"][0]["evidence"] = evidence
    assert any("source_revision does not match inventory commit_sha" in error
               for error in validate_inventory(report))


def test_rejects_pass_evidence_with_nonzero_exit_status():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "ACCEPTED"
    report["assets"][0]["verification_status"] = "PASS"
    evidence = valid_evidence()
    evidence[0]["exit_status"] = 1
    report["assets"][0]["evidence"] = evidence
    assert any("PASS evidence requires exit_status 0" in error
               for error in validate_inventory(report))


def test_rejects_fail_evidence_with_zero_exit_status():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "REJECTED"
    report["assets"][0]["verification_status"] = "FAIL"
    evidence = valid_evidence()
    evidence[0]["result"] = "FAIL"
    evidence[0]["exit_status"] = 0
    report["assets"][0]["evidence"] = evidence
    assert any("FAIL evidence requires a non-zero exit_status" in error
               for error in validate_inventory(report))



def test_rejects_evidence_when_inventory_commit_is_missing():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "ACCEPTED"
    report["assets"][0]["verification_status"] = "PASS"
    report["commit_sha"] = None
    report["assets"][0]["evidence"] = valid_evidence()
    assert any("evidence requires a non-empty inventory commit_sha" in error
               for error in validate_inventory(report))


def test_rejects_evidence_when_inventory_commit_is_blank():
    report = valid_report()
    report["assets"][0]["lifecycle_status"] = "ACCEPTED"
    report["assets"][0]["verification_status"] = "PASS"
    report["commit_sha"] = "  "
    report["assets"][0]["evidence"] = valid_evidence()
    assert any("evidence requires a non-empty inventory commit_sha" in error
               for error in validate_inventory(report))
