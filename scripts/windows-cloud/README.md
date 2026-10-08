# Electronic Brain — Windows Server 2025 Cloud Launch

One bounded deployment path; no success claims from Terraform output alone.

## Paths

- brain_v12/cloud/windows_terraform/backend.tf — Azure Blob remote-state backend.
- scripts/windows-cloud/bootstrap-state.ps1 — bootstraps the private state resource group/storage and can request Azure provider registration.
- scripts/windows-cloud/preflight.ps1 — checks OIDC variables, secret presence, provider registration, image availability and requested SKU.
- scripts/windows-cloud/configure-winrm.ps1 — configures guest WinRM over HTTPS through Azure Run Command.
- scripts/windows-cloud/verify.ps1 — verifies Azure provisioning state, running state, public IP, TCP/5986 and authenticated PowerShell remoting.
- scripts/windows-cloud/deploy.ps1 — single orchestrator: preflight → remote state → validate → plan → explicit apply → guest configuration → authenticated verification.

## GitHub Actions configuration

Environment variables in brain-windows-production:
- AZURE_CLIENT_ID
- AZURE_TENANT_ID
- AZURE_SUBSCRIPTION_ID
- Optional BRAIN_TFSTATE_ACCOUNT (globally unique, 3–24 lowercase letters/digits)

Environment secrets:
- BRAIN_WINDOWS_ADMIN_USERNAME
- BRAIN_WINDOWS_ADMIN_PASSWORD

Configure GitHub OIDC federation for this repository/environment. The Azure identity needs permission to register providers, create the dedicated state resource group/storage, write Blob state (Storage Blob Data Contributor on the state account), and provision/inspect the VM and network resources. Never commit credentials or state.

## First-time setup

1. Review subscription billing, quotas, and the intended region.
2. After Azure login, run bootstrap-state.ps1 -RegisterProviders. This creates a dedicated state resource group and private Standard_LRS storage, which can incur Azure charges. Wait until Compute, Network and Storage providers show Registered.
3. Set the GitHub OIDC variables and admin credentials secrets.
4. Run the Windows launch workflow manually with approve_apply=true. Ordinary pushes must not provision cloud resources.
5. Retain the workflow verification output as launch evidence.

## Local execution

Inject OIDC values and credentials through a secret manager/environment; never hardcode them.

Plan only:
    .\scripts\windows-cloud\deploy.ps1

Apply after reviewing the plan:
    .\scripts\windows-cloud\deploy.ps1 -Apply

## Safety and acceptance

- No 0.0.0.0/0 management rule.
- One orchestrator only; no recursive retries or parallel self-healing launch loops.
- Terraform state is remote; never commit *.tfstate, *.tfplan, or credentials.
- Terraform apply is not a successful launch.
- Success requires Azure provisioningState=Succeeded, powerState=VM running, TCP/5986 reachable from the allowed source, and authenticated remote PowerShell reporting the guest OS.
- If quota/capacity, provider registration, RBAC, OIDC, or networking fails, stop with evidence. Do not silently switch regions or create replacement resources.
