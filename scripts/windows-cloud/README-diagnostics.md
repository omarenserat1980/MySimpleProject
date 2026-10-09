# Read-only Azure Windows VM diagnostics

Run this script from a trusted Windows PowerShell terminal where Azure CLI is already installed and authenticated.

```powershell
# Inspect current Azure CLI account/subscription context (read-only):
az account show

# Run a read-only inventory for the expected Brain VM:
./scripts/windows-cloud/diagnose-azure-readonly.ps1

# Optionally scope all reads to a known subscription ID without switching the active subscription:
./scripts/windows-cloud/diagnose-azure-readonly.ps1 -SubscriptionId "<subscription-id>"
```

The script emits JSON for:
- Azure CLI availability and current account/subscription context (no credential values);
- target resource group and VM metadata/provisioning state/power state;
- VM network interface IDs, IP metadata, and effective NSG results when Azure returns them;
- Bastion resources visible in the selected subscription;
- recent Activity Log events for the target resource group (last 30 days, up to 50 entries).

## Safety boundary

- No resource creation, deletion, start/stop, deployment, Terraform execution, network edits, port probes, or subscription switching.
- It does not request, print, or persist passwords, tokens, client secrets, or private keys.
- A failed read is reported as missing/unreadable, not proof that a resource does not exist.
- Activity log output may include resource IDs and caller identity metadata; review/redact before sharing.
- A public IP, NSG rule, or successful Azure control-plane read does not prove Windows is booted, RDP is enabled, credentials are valid, or the network path is reachable.
- The script does not estimate Azure billing. Do not create Bastion or change VM size/networking as part of diagnosis.
- Run only in a trusted terminal after reviewing the script. It has not been executed against a live Azure subscription as part of this commit.
