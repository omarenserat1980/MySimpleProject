# Brain Cloud GCP Host

Provider-specific path for a small Google Cloud control-plane host. It does not make Brain dependent on Google Cloud.

## Target
- Compute Engine e2-micro
- Debian 12
- Docker + Compose
- persistent Brain state
- private Brain Git
- Brain Cloud Worker

Google currently lists one e2-micro Compute Engine VM, 30 GB standard persistent disk, and 1 GB/month outbound transfer in its Always Free Compute Engine allowance for eligible customers. The allowance is quota-based and subject to current Google terms. It is suitable for control-plane/coordination work, not heavy video generation or mining.

## Required setup
Create or choose a Google Cloud project with billing enabled. Free-tier quotas do not guarantee zero cost if they are exceeded.

Required GitHub Actions secrets:
- GCP_PROJECT_ID
- GCP_CREDENTIALS_JSON

Optional repository variables:
- BRAIN_GCP_REGION (default us-central1)
- BRAIN_GCP_ZONE (default us-central1-a)

Never commit service-account credentials.

## Security
- No public Brain Git exposure.
- No payment, withdrawal, publishing, contract, or external submission is enabled by provisioning.
- GitHub remains the external code/CI mirror until Brain Git is independently verified.
