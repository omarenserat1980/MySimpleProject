# Brain Azure Emulator

This is the pre-production cloud rehearsal layer. It models only the Azure
contracts Brain needs and never contacts Azure or creates billing.

## Rehearsal

Resource group -> VNet/subnet -> IP/NIC/disk -> Windows Server 2025 x86_64 VM
-> free-only capacity gate -> health evidence -> release gate.

## Real Azure boundary

The real provider is the final adapter only. Before provisioning it must pass:
- emulator release gate;
- free-capacity preflight;
- estimated cost == 0;
- required quota confirmed;
- Windows Server 2025 image availability;
- post-provision boot evidence;
- Brain health evidence.

**Principle: emulate everything possible; spend the real cloud call only on the
smallest irreversible boundary: creating and verifying the actual VM.**


## Acceptance verification

From the repository root, run:

```bash
PYTHONPATH=. python -m pytest -q brain_v12/tests/test_azure_emulator.py brain_v12/tests/test_azure_emulator_acceptance.py brain_v12/tests/test_azure_emulator_windows_provider.py brain_v12/tests/test_azure_handoff.py brain_v12/tests/test_azure_handoff_ledger.py brain_v12/tests/test_real_azure_adapter.py
PYTHONPATH=. python -m brain_v12.azure_emulator.launch
```

The launch command writes `.brain/state/azure-emulator-evidence.json`. Evidence must carry `provenance: SIMULATED`; it proves emulator behavior only, not a real Windows boot or Azure resource creation. Real-cloud provisioning stays separately gated.
