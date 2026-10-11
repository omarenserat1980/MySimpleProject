# Golden Loop Accelerator

A read-only evidence triage tool to reduce repeated manual investigation. It scans a downloaded workflow-artifact directory, evaluates the runner, executor, signed-contract gate, guest boot evidence, and independent completion gate, then prints the blockers in a fixed order with the next safe action.

## Fast path

From the repository root:

```bash
python3 -m unittest brain_v12.tests.test_golden_loop_accelerator -v
python3 -m brain_v12.tools.golden_loop_accelerator --root brain6_artifacts --output brain6_artifacts/golden-loop-accelerator-report.json
```

If the evidence belongs to a known GitHub Actions run, bind the audit to it:

```bash
python3 -m brain_v12.tools.golden_loop_accelerator \
  --root brain6_artifacts \
  --expected-run-id 38124594227 \
  --output brain6_artifacts/golden-loop-accelerator-report.json
```

Download/extract artifacts for that run into the scan root first. Do not mix artifacts from separate runs or attempts. The tool reports mixed run IDs and fails closed if the requested run ID does not match.

## Gate order

1. **Runner:** health verified, online, execution probe PASS, runtime surface PASS.
2. **Executor:** trusted executor attestation says verified and identifies the executor.
3. **Contract:** contract gate explicitly reports a verified/valid signed contract.
4. **Guest boot:** guest marker, Windows Server 2025 identity, and boot timestamp are present.
5. **Completion:** independent gate status is exactly `WINDOWS_BOOT_VERIFIED` with no reasons.

The tool returns exit code 0 only when all five evidence classes pass. It returns 2 when evidence is missing, malformed, invalid, or incomplete; 4 for an invalid scan root. It emits JSON suitable for a later dashboard or CI artifact.

## Safety boundaries

- Read-only: no network calls, secret changes, contract issuance, VM start, or cloud provisioning.
- Does not inspect or print contract bodies, signing keys, tokens, or credential values.
- Missing or malformed evidence never counts as success.
- A passing executor gate is not Windows boot proof.
- This report is a triage aid, not a replacement for the authoritative Windows completion gate.
