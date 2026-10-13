"""Regression tests for truthful deployment identity diagnostics."""
import os

from brain_v12 import app as brain_app


def _snapshot(monkeypatch, *, actual, expected=None, github_sha=None):
    monkeypatch.setattr(brain_app, "DEPLOY_COMMIT", actual)
    monkeypatch.delenv("BRAIN_EXPECTED_COMMIT", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    if expected is not None:
        monkeypatch.setenv("BRAIN_EXPECTED_COMMIT", expected)
    if github_sha is not None:
        monkeypatch.setenv("GITHUB_SHA", github_sha)
    return brain_app._deployment_snapshot()


def test_missing_independent_expected_commit_is_unverifiable(monkeypatch):
    snapshot = _snapshot(monkeypatch, actual="abc123")
    assert snapshot["convergence_status"] == "unverifiable"
    assert snapshot["converged"] is False
    assert snapshot["expected_commit"] is None


def test_matching_independent_expected_commit_is_verified(monkeypatch):
    snapshot = _snapshot(monkeypatch, actual="abc123", expected="abc123")
    assert snapshot["convergence_status"] == "matched"
    assert snapshot["converged"] is True


def test_mismatched_independent_expected_commit_is_not_verified(monkeypatch):
    snapshot = _snapshot(monkeypatch, actual="abc123", expected="def456")
    assert snapshot["convergence_status"] == "mismatched"
    assert snapshot["converged"] is False


def test_github_sha_remains_an_independent_expected_commit(monkeypatch):
    snapshot = _snapshot(monkeypatch, actual="abc123", github_sha="abc123")
    assert snapshot["convergence_status"] == "matched"
    assert snapshot["converged"] is True
