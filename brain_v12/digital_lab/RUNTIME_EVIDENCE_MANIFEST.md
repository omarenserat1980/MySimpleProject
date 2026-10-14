# Brain Digital Lab — Runtime Evidence Manifest

The runtime evidence gate consumes observations collected by existing test, health,
device, or deployment workflows. It does **not** run probes or execute inventoried
assets itself.

## Manifest shape

A JSON object contains:

- `schema_version`: integer `1`
- `source_revision`: exact commit SHA or other immutable revision tested
- `generated_utc`: UTC observation-generation timestamp
- `components`: non-empty list of component evidence records

Each component record includes `component_id`, `domain`, `required`, `result`,
`source_revision`, `check_id`, `reference`, `observed_utc`, `exit_status`,
`scope`, and `limitations`.

Allowed results are `PASS`, `FAIL`, `BLOCKED`, and `NOT_RUN`. A pass requires
exit status 0; a failure requires a non-zero exit status; blocked and not-run
records require a null exit status. Every component's revision must match the
manifest revision.

## Gate behavior

- `READY`: all required records are valid and `PASS`.
- `FAIL`: at least one required record has a valid `FAIL` result.
- `BLOCKED`: at least one required record is `BLOCKED` or `NOT_RUN`, with no
  required failure.
- `INVALID`: the manifest is malformed, evidence is incomplete, or revisions
  do not match.

Malformed or missing evidence never becomes a pass. Optional components are still
validated, but their non-pass result does not block the required-component gate.

## Run

```sh
PYTHONPATH=. python -m brain_v12.digital_lab.runtime_evidence path/to/runtime-evidence.json
PYTHONPATH=. python -m pytest -q brain_v12/tests/test_digital_lab_runtime_evidence.py
```

Exit code is 0 only for `READY`; all other gate states exit 2. This is a validator
for supplied evidence, not independent proof that a service, device, server, ASIC,
or payment system is live. Evidence references should point to durable run logs or
artifacts; secrets and personal data must not be included.
