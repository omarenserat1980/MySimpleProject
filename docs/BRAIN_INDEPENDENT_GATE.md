# Brain Independent Gate

The Independent Executor Pool must be verifiable without Windows, arkan, or a
GitHub Actions runner.

Run from the repository root:
python3 tools/brain_independent_gate.py

Or on Termux/Linux:
bash tools/run_brain_independent_gate.sh

Evidence is written to:
brain6_artifacts/independence_gate/independence_gate.json

The evidence contains the real pytest return code and captured output.
status=PASS is written only when pytest returns exit code 0.

GitHub Actions is a secondary CI/evidence channel, not the Brain runtime
authority. ARKAN_OFFLINE != BRAIN_DOWN.
