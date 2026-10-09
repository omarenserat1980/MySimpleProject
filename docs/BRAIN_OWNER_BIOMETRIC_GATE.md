# Brain Owner Biometric Gate — Implementation Status

## Scope
This branch adds an Android system biometric prompt before the optional Android Executor starts. The OS performs biometric matching; the app does not read, export, or store fingerprint images/templates.

## Changes
- MainActivity asks for Android's system biometric authentication before saving the executor configuration and starting the foreground service.
- AndroidManifest declares `USE_BIOMETRIC`.
- Devices below Android 9 (API 28) are blocked by this initial implementation rather than silently bypassing verification.
- The UI explicitly states that this is a local start gate, not a server-verified identity.

## Security boundary — important
This change is **not yet a complete Brain owner identity system**. It only gates starting this Android client. It does not prove identity to the Brain API, bind authentication to a server challenge, protect the configured agent key with Android Keystore, or secure remote admin endpoints. Do not grant cloud administrator privileges based only on this local prompt.

## Required next steps
1. Build the APK in CI and test on a physical Android device with biometric enrollment.
2. Add an Android Keystore key requiring per-use biometric authentication and sign a fresh server challenge.
3. Verify the signature server-side against a registered public key before issuing a short-lived owner session.
4. Add replay protection, session expiry/revocation, audit events, and a recovery method.
5. Add tests for success, mismatch, cancellation, lockout, missing enrollment, API < 28, and changed biometric enrollment.

## Acceptance criteria
- No executor start on mismatch, cancellation, or biometric error.
- No fingerprint data leaves Android's biometric subsystem.
- No cloud owner/admin access without server-side cryptographic verification.
- Report PASS only after CI build and physical-device tests provide evidence.
