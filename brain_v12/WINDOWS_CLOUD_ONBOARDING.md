# Windows Server 2025 Cloud Onboarding

This is the Brain-owned onboarding path for a real Windows Server 2025 cloud VM.

## 1. Provision the VM

Provision a real Windows Server 2025 x86_64 VM with your chosen cloud provider.
Do not put provider credentials in this repository.

Required guest capability:
- Windows Server 2025
- x86_64/AMD64
- outbound HTTPS to the Brain Fabric endpoint

## 2. Create a Brain enrollment

From an authenticated Brain administrator environment:

```bash
python -m brain_v12.tools.enroll_windows_cloud_node \
  --fabric-url "$BRAIN_FABRIC_URL" \
  --node-id "win-cloud-01" \
  --control-token "$BRAIN_CONTROL_TOKEN"
```

The enrollment token is short-lived and must be delivered to the VM through a secure administrative channel. Never commit it.

## 3. Configure the Windows VM

Set:
- `BRAIN_FABRIC_URL`
- `BRAIN_WINDOWS_NODE_ID`
- `BRAIN_ENROLLMENT_TOKEN`

Then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\brain_v12\tools\windows_cloud_heartbeat.ps1
```

The script refuses to register a non-Windows Server 2025 or non-64-bit guest.

## 4. Verify from Brain

Call:

```
GET /api/brain/windows/cloud/status
```

Expected verified state:

```json
{
  "status": "WINDOWS_CLOUD_AVAILABLE",
  "verified": true
}
```

No heartbeat means no availability. A stale heartbeat is rejected.

## Security boundary

The provider account, VM credentials, and enrollment token stay outside Git.
GitHub remains source/evidence control; it is not the Windows runtime.
