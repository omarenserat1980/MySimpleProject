import pytest

from brain_v12.brain.github_simulator import BrainGitHubSimulator, GitHubSimulationError, self_test


def test_simulated_branch_commit_pr_and_workflow():
    sim = BrainGitHubSimulator("openai/example")
    assert sim.create_branch("feature/demo")["simulated"] is True
    commit = sim.commit_file("feature/demo", "hello.txt", "hello\n", "Add hello")
    assert commit["ok"] is True
    pr = sim.open_pull_request("Test PR", "feature/demo")
    assert pr["draft"] is True
    run = sim.run_workflow("checks", "feature/demo", {"tests": True, "lint": True})
    assert run["conclusion"] == "success"
    assert run["hosted_github_actions"] is False


def test_failed_simulated_check_is_failure_not_pass():
    sim = BrainGitHubSimulator()
    result = sim.run_workflow("checks", "main", {"tests": True, "security": False})
    assert result["conclusion"] == "failure"


def test_reject_duplicate_branch_and_missing_base():
    sim = BrainGitHubSimulator()
    with pytest.raises(GitHubSimulationError, match="SIM_BRANCH_NAME_INVALID_OR_EXISTS"):
        sim.create_branch("main")
    with pytest.raises(GitHubSimulationError, match="SIM_BASE_BRANCH_NOT_FOUND"):
        sim.create_branch("feature", "missing")


def test_reject_unsafe_path_and_invalid_pull_request():
    sim = BrainGitHubSimulator()
    with pytest.raises(GitHubSimulationError, match="SIM_FILE_PATH_OR_MESSAGE_INVALID"):
        sim.commit_file("main", "../secrets.txt", "no", "bad path")
    with pytest.raises(GitHubSimulationError, match="SIM_PULL_REQUEST_INPUT_INVALID"):
        sim.open_pull_request("Invalid", "main", "main")


def test_self_test_is_explicitly_simulated():
    result = self_test()
    assert result["ok"] is True
    assert result["snapshot"]["external_github_calls"] is False
    assert result["snapshot"]["hosted_workflows_run"] is False
