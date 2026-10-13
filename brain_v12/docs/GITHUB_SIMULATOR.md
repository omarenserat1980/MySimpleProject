# Brain GitHub Simulator

`brain_v12/brain/github_simulator.py` is an isolated, deterministic, in-memory model of a small GitHub workflow.

## What it simulates

- Creating branches from another simulated branch
- Committing text files to simulated branch state
- Opening draft pull requests
- Recording workflow checks as simulated success/failure
- Returning a snapshot that explicitly marks external actions as disabled

## Run the self-test

From the repository root:

```bash
python -c "from brain_v12.brain.github_simulator import self_test; print(self_test())"
```

## Safety boundary

This is **not a GitHub API client**. It makes no network calls, does not read tokens or secrets, does not push commits, does not create real pull requests, and does not run hosted GitHub Actions. A simulated green check is not evidence that a real GitHub workflow passed.
