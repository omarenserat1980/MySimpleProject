# Alexa Azure VM Simulator

## Purpose
Model the proposed **Alexa** cloud VM configuration for Windows Server 2025 without depending on Arkan or requiring an Azure account. This is a planning and test component only.

## Run
From the repository root:

```bash
python -m brain_v12.brain.azure_vm_simulator
python -m brain_v12.brain.azure_vm_simulator --region uaenorth --output alexa-azure-plan.json
python -m unittest brain_v12.tests.test_azure_vm_simulator -v
```

The default plan uses the Windows Server 2025 Datacenter marketplace image identifier and a sample VM size. Availability, quota, price, subscription eligibility, and region support are not verified by this simulator.

## Safety boundary
Every result contains `simulation: true`, `azure_api_called: false`, `resource_created: false`, and `real_boot_verified: false`. The simulator never authenticates to Azure, creates resources, downloads an image, or starts a guest OS. A successful simulated plan is not evidence that Azure resources exist or that Windows booted.

## Real deployment path
A future Azure adapter must be separately implemented with explicit subscription/resource-group selection, least-privilege identity, budget/quotas preflight, owner approval, and deployment evidence. A real-boot success must require guest-side Windows Server 2025 evidence collected from the actual VM and independently verified. Never reuse the Arkan executor identity for Alexa.
