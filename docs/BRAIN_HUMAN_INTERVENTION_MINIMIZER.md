# Human Intervention Minimizer

## Purpose

`brain_v12/tools/human_intervention_minimizer.py` inspects a local Electronic Brain checkout and reports safe recovery actions plus unresolved authority gates. It is intended to reduce repeated manual diagnosis without converting missing authority or evidence into a false success.

## Usage

Inspect the current checkout:

```bash
python brain_v12/tools/human_intervention_minimizer.py --repo "$HOME/MySimpleProject"
```

Allow a side-by-side clean checkout when the current repository is divergent or the runner-watch helper is missing:

```bash
python brain_v12/tools/human_intervention_minimizer.py \
  --repo "$HOME/MySimpleProject" \
  --repair-safe \
  --destination "$HOME/MySimpleProject-main-clean" \
  --output "$HOME/brain-recovery-report.json"
```

The destination is never overwritten. Review the JSON report and confirm the resulting checkout before using it. The tool fetches `origin/main` to compare commits; network/authentication failures are reported as blockers.

## Remaining external gates

- An owner-authorized GitHub token that can read the repository runner endpoint and an authenticated `gh` identity allowed to write Actions secrets.
- A real, pre-issued, signed Windows execution contract from the authorized Brain Control Plane.
- A trusted runner that is online and passes the explicit execution probe.
- Same-run guest evidence proving Windows Server 2025 booted from the installed disk.

The tool does not generate credentials, write secrets, create approvals or signatures, change repository permissions, provision paid resources, or claim real boot. Those gates remain blocked until authoritative evidence is supplied.

## Validation

Run the focused tests:

```bash
python -m unittest brain_v12.tests.test_human_intervention_minimizer -v
```

A passing unit test validates the local safety behavior only; it does not prove GitHub runner readiness or Windows boot.
