# Retired Brain V7 Cloud Runbook

**Status: RETIRED.** This document is preserved for historical traceability only. Do not deploy the former Brain V7 worker.

## Canonical runtime

Use the Brain V12 API entrypoint:

```bash
python -m brain_v12.app
```

The compatibility Dockerfiles under this directory now start Brain V12 and do not invoke the V7 worker.

## Media generation status

The former V7 media worker is not an approved fallback. Brain V12-native rendering is not yet integrated into `cloud/film_reliability.py`; film jobs must fail closed with `BRAIN_V12_RENDERER_NOT_INTEGRATED` rather than generate a misleading completion record.

## Device and Windows status

The intended runtime is independent of Arkan, Redmi 3, Termux, and Hyper-V. This is an architecture goal, not proof that a cloud executor is authenticated or that Windows Server 2025 has booted. A real Windows boot requires guest-origin evidence from the installed disk and a passing completion gate. Installer-only/QEMU TCG evidence is not accepted as a real boot.

## Secrets and stop controls

Never commit tokens, payment credentials, wallet keys, or private keys. Configure credentials only through the authorized secret store. Historical stop flags are not evidence that an old service is still installed or stopped on a host.
