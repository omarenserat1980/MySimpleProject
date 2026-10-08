# Cloud Executor Activation

The production Windows executor is a Brain-owned Linux x86_64 cloud VM.

## Activation

On the cloud VM, provide these host environment values:

- `BRAIN_CLOUD_EXECUTOR=1`
- `BRAIN_CLOUD_EXECUTOR_ID`
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION`

Then run:

```bash
./tools/bootstrap_brain_cloud_executor.sh
```

The bootstrap refuses to register unless x86_64, /dev/kvm, QEMU, OVMF tooling and
the Cloud Executor Gate all pass. It registers the GitHub runner with the complete
Brain Cloud labels and starts it as a service.

## Critical boundary

The workflow never sets Cloud Executor identity. The host does.

Registration alone is not success. The executor must pass:

1. Cloud Executor Gate.
2. Brain Authority contract.
3. Windows Server 2025 real boot.
4. Independent Windows completion gate.
5. Evidence preservation.

Only then may the system emit `BRAIN_WINDOWS_REAL_BOOT_CLOSED_LOOP=VERIFIED`.
