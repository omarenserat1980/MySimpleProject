# Read-only Azure Windows VM diagnostics

Run this script from a trusted Windows PowerShell terminal where Azure CLI is already installed.

```powershell
# Check the currently selected Azure CLI subscription without changing it:
az account show

# Run a read-only inventory for the Brain VM:
./scripts/windows-cloud/diagnose-azure-readonly.ps1

# Optionally scope reads to a known subscription ID without switching the active subscription:
./scripts/windows-cloud/diagnose-azure-readonly.ps1 -SubscriptionId "<subscription-id>"
```

The script inspects Azure CLI authentication context, the expected resource group and VM, power state, NIC/public-IP metadata, NSG rule summaries, and Bastion hosts in the same resource group. It emits JSON and does not request or print passwords/tokens.

## Safety boundary

- No resource creation, deletion, start/stop, deployment, Terraform, network edits, port probes, or subscription switching.
- A failed read is reported as not found/unreadable, not proof that a resource does not exist.
- Bastion in another resource group may not be detected by this scoped inventory.
- A public IP or NSG rule alone does not prove RDP reachability; check effective security rules and VM-side firewall separately.
- The script does not estimate Azure billing. Do not create Bastion or change VM size/networking as part of diagnosis.
