# Read-only Windows image inspection runbook

## Purpose and boundary

`brain_v12/tools/windows_image_inspect_readonly.ps1` performs a metadata query using DISM and records file identity before and after the query. It does not mount, service, execute, or modify the image. The script has not been executed against a real image as part of this change; use it only on an authorized Windows host with DISM installed.

Supported direct input formats are `.wim`, `.vhd`, `.vhdx`, and `.ffu`. An ISO is a container, not a direct `DISM /Get-ImageInfo` target. Extract or otherwise access its Windows image file using an approved read-only workflow first; preserve and separately fingerprint the original ISO. Do not rename a file to disguise its actual format.

## Run

Open PowerShell on a Windows host with DISM available:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\brain_v12\tools\windows_image_inspect_readonly.ps1 -ImagePath 'D:\AuthorizedMedia\install.wim' -OutputPath 'D:\Evidence\windows-image-inspection.json'
```

The execution-policy command only changes the current PowerShell process. Follow local organization policy; do not bypass policy where prohibited.

For VHD, VHDX, and FFU, the script requests index 1 as required by DISM. WIM queries return image metadata for the available indexes.

## Output fields

- `sha256_before` and `sha256_after`: identity comparison, not proof of Microsoft publisher authenticity.
- `file_metadata_unchanged`: compares hash, size, and last-write timestamp after the query.
- `dism_exit_code` and `dism_output`: raw tool result for later review.
- `image_mounted`, `image_serviced`, `guest_boot_verified`: remain false; this tool cannot establish those states.

A nonzero DISM exit code, hash mismatch, or metadata change is a failed inspection and must not be promoted to verified evidence. Keep reports alongside a trusted audit trail and bind them to the exact artifact manifest.

## Independent SHA-256 comparison

Use `brain_v12/tools/windows_artifact_hash_verify.ps1` to compare an artifact against a SHA-256 value obtained independently from an authoritative source. Do not copy the expected hash from the artifact manifest itself; that would only compare the file to its own claim.

```powershell
.\brain_v12\tools\windows_artifact_hash_verify.ps1 `
  -ArtifactPath 'D:\AuthorizedMedia\WindowsServer2025.iso' `
  -ExpectedSha256 '<64-hex-digest-from-an-independently-reviewed-source>' `
  -TrustedReferenceUrl 'https://www.microsoft.com/<official-media-reference>' `
  -OutputPath 'D:\Evidence\windows-artifact-hash-check.json'
```

The tool refuses to overwrite the artifact or an existing evidence file. A matching digest proves only that the bytes match the supplied digest. The report deliberately sets `reference_independently_reviewed`, `publisher_authenticity_verified`, and `real_guest_boot_verified` to false: a URL string and hash comparison do not establish that the reference is authentic or that the OS booted.

## Next gate

1. Review the manifest and independently verify publisher signature/provenance through an approved mechanism.
2. Run this script on an authorized Windows host against the exact artifact.
3. Review output and confirm the original image hash is unchanged.
4. Only then design a separate servicing workflow using a disposable copy.
5. Real boot requires separate guest-generated evidence tied to the exact image and VM configuration. This report is not boot evidence.

Official reference: https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/dism-image-management-command-line-options-s14?view=windows-11