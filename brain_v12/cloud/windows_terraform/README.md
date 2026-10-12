# Brain Windows Cloud Terraform

This directory defines the Azure infrastructure contract for a real
Windows Server 2025 Brain node.

Safety:
- Never commit Azure credentials, administrator passwords, or Terraform state.
- Use the runtime's Azure authentication mechanism.
- Restrict allowed_source_ip to a trusted CIDR.
- Generate and review a Terraform plan before apply.
- Brain verification still requires a fresh Windows agent heartbeat.

Required Brain outputs:
- brain_vm_id
- brain_provider
- brain_region
- brain_state
- brain_os
- brain_architecture

This template is infrastructure code, not proof that a VM exists.
