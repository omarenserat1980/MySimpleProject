# Blocker-to-Tool Toolkit

## Purpose
Turn recurring cloud Windows boot failures into structured diagnostics. The tool checks executor architecture, /dev/kvm access, QEMU/media utilities, executor identity, and presence of protected configuration variables.

## Run
    python3 brain_v12/brain/blocker_diagnostic.py
    python3 brain_v12/brain/blocker_diagnostic.py --output artifacts/blocker-diagnostic.json
    python3 -m unittest brain_v12/tests/test_blocker_diagnostic.py -v

Exit code is 0 only when all preflight checks pass; otherwise 2. Missing secret names may be reported, but secret values are never printed or persisted.

## Safety and evidence boundaries
- This tool does not call Azure/GitHub APIs, create cloud resources, write secrets, or install packages.
- A present environment variable proves presence only, not that its value is valid or authorized.
- A passing preflight is not proof of a registered trusted runner or successful Windows boot.
- The report always keeps windows_boot_verified=false; only the independent Windows completion gate can produce WINDOWS_BOOT_VERIFIED from complete, validated evidence.
- Next stage: repair the named blocker, rerun this check, run the existing cloud executor gate, then the real-boot workflow and independent completion gate.
