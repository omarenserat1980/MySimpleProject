# Windows Server 2025 Evidence Checklist

## Goal

Move from metadata-only validation to independently reviewable evidence for one specifically identified, legally obtained Windows Server 2025 image. This checklist is a procedure, not evidence that any step has already run.

## Gate 0 — Identify the artifact

- [ ] Record the exact filename, format, byte size, acquisition time (UTC), and SHA-256.
- [ ] Record the official acquisition/reference URL and applicable license/provenance.
- [ ] Obtain the expected digest independently from an authoritative source, where Microsoft publishes one.
- [ ] Do not treat a manifest's own digest or a URL string as proof of publisher authenticity.
- [ ] Never commit the Windows image, license key, access token, or other secret to Git.

**Pass condition:** metadata is complete and the digest has an independently documented reference. A syntactically valid manifest alone is not a pass for authenticity.

## Gate 1 — Read-only host inspection

On an authorized Windows host with DISM available:

1. Preserve the original image unchanged and keep its SHA-256.
2. For ISO media, use an approved read-only method to access the contained WIM/ESD; keep the original ISO fingerprint separately. Do not pass an ISO directly to `DISM /Get-ImageInfo`.
3. Run `brain_v12/tools/windows_image_inspect_readonly.ps1` against the appropriate WIM/VHD/VHDX/FFU input.
4. Run `brain_v12/tools/windows_artifact_hash_verify.ps1` using the independently obtained expected digest.
5. Retain the JSON reports and raw DISM output in an access-controlled evidence directory outside the repository.
6. Review exit codes, before/after hashes, paths, timestamps, and whether the original file remained unchanged.

**Pass condition:** tool exits successfully, artifact hash matches the independent reference, and the report is reviewed. This is still not a guest boot or a cryptographic attestation of the evidence producer.

## Gate 2 — Disposable VM preparation

- [ ] Use a supported hypervisor and an isolated, disposable VM/disk copy.
- [ ] Record hypervisor/version, VM configuration, virtual firmware mode, boot media, virtual disk identity, and configuration SHA-256.
- [ ] Keep host observations distinct from guest-reported facts.
- [ ] Do not use the low-memory development PC as a required dependency; use an available authorized host or stop if no suitable environment exists.
- [ ] Do not download or provision paid infrastructure automatically.

**Pass condition:** VM configuration and source-image identity are recorded. VM creation alone does not prove that Windows booted.

## Gate 3 — Guest boot evidence

After actually booting the VM, collect evidence from inside the guest for:

- Windows edition and build;
- UTC boot timestamp;
- a unique run/evidence ID;
- VM configuration fingerprint and source artifact SHA-256;
- guest-side command output plus host-side run correlation;
- integrity/provenance of the evidence collector and an independent verifier's result.

An independently signed/attested evidence envelope is required before a trusted service may promote state. A JSON object with `independent_verification: true` is not itself trusted verification.

**Pass condition:** an independent verifier validates the producer/attestation, binds the evidence to the exact artifact and VM configuration, and confirms the guest boot event. Otherwise keep `real_guest_boot_verified = false`.

## Required state separation

| State | Meaning |
|---|---|
| `SIMULATED` | Synthetic event only |
| `ARTIFACT_FINGERPRINTED` | Manifest metadata validated; SHA-256 syntax/value recorded, not necessarily independently authenticated |
| `HOST_INSPECTION_RECORDED` | Read-only host tool output exists and is reviewed |
| `ARTIFACT_AUTHENTICITY_VERIFIED` | Trusted signature/provenance verifier confirms publisher authenticity |
| `GUEST_BOOT_VERIFIED` | Independently verified guest evidence confirms boot of the identified image |

Do not infer a higher state from a lower one. In particular, a successful GitHub Actions run, a simulator result, a matching self-supplied hash, or a manifest claim does not prove real Windows boot.

## Current known boundary

The manifest validator and read-only PowerShell helpers exist in the repository. Unless a new evidence artifact is attached and independently reviewed, no real Windows Server 2025 image inspection, servicing operation, or guest boot should be reported as completed.
