# Arkan ASUS Golden Loop Mission

## Mission identity

- Mission ID: `ARKAN_ASUS_COMPUTER_BUILD`
- Target: the physical ASUS VivoBook known as Arkan, not a GitHub-hosted runner or simulator.
- Goal: reach a verified, recoverable Brain development host; only then continue the Windows Server 2025 VM build.
- Current state: `OPEN_NOT_CLOSED`; the physical-host observation has not yet been submitted and verified.
- Retry policy: diagnose once, classify one blocker at a time, and allow at most two retries per failed gate before pausing for a human decision.

## One closed loop

`INTENT → PLAN → AUTHORITY → ADMIT → EXECUTE → OBSERVE → VERIFY → COMMIT → LEARN → CLOSED`

On failure: `RECOVER → bounded retry → VERIFY`. A missing or stale host report returns to `OBSERVE`; it must never be replaced by a CI report or synthetic fixture.

## Current execution slice

1. **Intent:** establish actual Arkan ASUS hardware, Windows build, available RAM/storage, firmware virtualization, Hyper-V availability, existing VM/VHDX/ISO state, and loopback Brain readiness.
2. **Plan:** run `tools/windows/arkan_asus_golden_probe.ps1` with read-only defaults. Supply `-WindowsServerIsoPath` only if the exact ISO path is known.
3. **Authority:** this observation requires no elevation and changes nothing. VM creation/start, Windows feature changes, package installs, disk edits, cloud provisioning, and public listeners are explicitly outside this slice and require a separate approval gate.
4. **Admit:** only a fresh report from the actual target host with a valid SHA-256 payload fingerprint is eligible. Hostname/model and timestamp must be inspected; a GitHub runner or simulated host is rejected. The probe deliberately sets `real_host_evidence=false` until a reviewer verifies the reported identity. It writes `arkan-asus-golden-observation.json` into the current working directory; share that file or its complete contents for review.
5. **Execute/observe:** execute the read-only probe on Arkan. It does not start or stop a VM or Brain process.
6. **Verify:** compare the report against the expected machine; review free memory, free disk, firmware virtualization, Hyper-V, target VM, VHDX, ISO, and API status. Unknown is not pass.
7. **Commit/learn:** store the report outside Git if it contains machine-specific details; record only the accepted findings and next blocker in the mission log.
8. **Close gate:** this observation slice may be accepted only after a fresh real-host report is reviewed. **The overall computer-build mission stays open** until a separately approved build plan is executed and verified.

## Acceptance criteria

- `host_identity`: real Arkan host identity and Windows details are present.
- `memory_headroom` and `system_disk`: actual available resources are measured before any VM attempt; no resource threshold is guessed.
- `firmware_virtualization`: firmware virtualization and SLAT are `PASS`, or the blocker is recorded.
- `hyperv_management`: Hyper-V management capability is identified.
- `target_vm`, `target_vhdx`, and `windows_server_iso`: observed states match the actual machine; `UNKNOWN` is not a pass.
- `brain_loopback_api`: local readiness is reported without contacting a remote endpoint.
- Report includes `payload_sha256`, observation time, stage, and safety assertions.
- No claim of Windows Server boot, Brain runtime readiness, or mission closure is allowed until separately collected live evidence proves it.

## Run on the actual ASUS

Open PowerShell in the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows\arkan_asus_golden_probe.ps1
```

If the ISO path is known, pass the exact path explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows\arkan_asus_golden_probe.ps1 -WindowsServerIsoPath 'C:\exact\path\WindowsServer2025.iso'
```

Copy the JSON between the observation markers, including `payload_sha256`, into the review channel. Do not commit the raw host report: it is machine-specific evidence. Never send secrets; the probe does not collect them.

## Safety and reality gate

- The probe is read-only and local-only; it does not enable Hyper-V, install software, start/stop services or VMs, modify disks, or create cloud resources.
- The probe's hash proves integrity of the captured payload, not that the report is truthful by itself. Verify host identity and freshness separately.
- A GitHub-hosted Windows runner passing PowerShell parsing is code validation only; it is not evidence from Arkan.
- The previous low-memory VM start failure is a reason to measure current free memory and avoid retrying VM boot blindly.
- No paid cloud provider, merge to `main`, or irreversible operation is part of this mission slice.
