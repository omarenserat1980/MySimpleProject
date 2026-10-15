# PHONE-ONLY Android Executor v1

## Runtime layers

Brain API -> Foreground Executor -> Task Policy -> Android/File/Toybox adapters -> Verification -> Report.

## Safety boundary

The executor does not expose an unrestricted remote shell. Tasks are allowlisted and file paths are confined to the ElectronicBrain factory output root.

## Media pipeline

The next media adapter uses an app-private FFmpeg binary when supplied. It must be installed/bundled explicitly; the executor does not download executable binaries at runtime.

## Verification

A task returning exit code 0 is only execution success. The factory still needs artifact verification (existence, size, checksum and media-specific checks) before marking a production operation VERIFIED.

## Recovery

Transient failures use bounded exponential backoff. Persistent failures are reported to the Brain instead of looping indefinitely.

## Local Android Key Attestation export (manual, opt-in)

The **CREATE & EXPORT ATTESTATION CHAIN** action is an explicit foreground user
operation. Paste the Base64-encoded challenge bytes issued by an independent
enrollment authority only after verifying their origin/signature outside this
app. The app does not authenticate the authority or verify a challenge signature.
The challenge must contain at least 32 bytes.

The user chooses a JSON destination before the app asks Android Keystore to
create the `brain-phone-identity-p256-v1` key. Existing aliases are never
replaced automatically. The exported file contains the public key and certificate
chain, the key fingerprint, and the challenge hash; it does not contain the
private key or the raw challenge. Keep the file local until a separately reviewed
verifier and transport are available.

Export is evidence capture only. The app does not validate certificate roots,
check revocation, upload evidence, register a node, grant trust, activate the
node, or start mining. A successful export is classified as
`LOCAL_ATTESTATION_CHAIN_UNVERIFIED`; independent verification and manual
approval remain required. If key creation succeeds but file writing fails, do
not retry blindly: the alias is intentionally non-overwritable.
