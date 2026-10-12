# Windows Cloud Launch: protected preflight configuration

The `BRAIN Windows Cloud Launch` workflow validates its configuration before Azure login or resource changes.

## Required environment variables

Configure these under GitHub **Settings → Environments → brain-windows-production → Environment variables**:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `BRAIN_ALLOWED_SOURCE_IP`: the trusted IPv4 CIDR allowed to reach the Windows management endpoint. Use the narrowest range possible (typically a single trusted public IPv4 address with `/32`). Do not use `0.0.0.0/0`.

Optional environment variable:

- `BRAIN_TFSTATE_ACCOUNT`: a globally unique Azure Storage account name, 3–24 lowercase letters/digits. If omitted, the bootstrap and deploy scripts derive the same deterministic name from the subscription ID.

Configure these under **Environment secrets** when an approved deployment is intended:

- `BRAIN_WINDOWS_ADMIN_USERNAME`
- `BRAIN_WINDOWS_ADMIN_PASSWORD`

The preflight-only mode does not require the Windows administrator secrets. An approved deployment does.

## Safety behavior

- The workflow validates required values before Azure login.
- Values are never printed to workflow logs.
- An invalid source CIDR or explicitly configured invalid state account blocks the run before cloud changes.
- A missing `BRAIN_TFSTATE_ACCOUNT` is not itself an error: existing bootstrap and deploy scripts intentionally derive a matching fallback.
- `approve_apply=false` is the safe preflight mode. Set `approve_apply=true` only when resource creation and Azure charges are authorized.
- Passing preflight is not proof of a running Windows Server. Deployment and final Windows management verification remain separate gates.
