# YouTube Control Plane

The YouTube Control Plane is the top-level pure decision facade for the content factory.

## Inputs

Channel strategy, video candidate, video economics, QC report, content fingerprint, existing fingerprints, and optional measurement.

## Order of control

1. Verify content identity.
2. Detect duplicate content.
3. Evaluate channel viability.
4. Evaluate video selection.
5. Evaluate video economics.
6. Evaluate technical/cinematic QC.
7. Return the next action.
8. Emit an auditable deterministic decision record.

## Safety

The control plane does not upload videos, create channels, spend money, or claim revenue. It only produces a decision for the single Brain orchestrator.

A duplicate is always blocked even if the video would otherwise pass every other gate.

## Financial separation

No YouTube analytics or forecast can settle the Economic Ledger. Confirmed revenue still requires the existing payment-evidence and settlement path.
