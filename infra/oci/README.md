# Brain Cloud OCI Host

This stack provisions a Linux VM for the Brain Cloud Worker using Oracle Cloud Infrastructure (OCI) Always Free eligible resources.

Target: Ubuntu Linux, OCI Ampere A1 Flex, up to 2 OCPUs/12 GB RAM, public IPv4, Docker, Compose, systemd, persistent worker state.

Required GitHub Actions secrets:
- OCI_TENANCY_OCID
- OCI_USER_OCID
- OCI_FINGERPRINT
- OCI_PRIVATE_KEY
- OCI_REGION
- OCI_COMPARTMENT_OCID
- BRAIN_SSH_PUBLIC_KEY

The OCI private key must never be committed.

Run the **Brain Cloud OCI Provision** workflow manually after the secrets exist. It creates the network, firewall, VM and bootstrap. The VM clones the repository, builds the worker image, and starts it under Docker/systemd.

No payment, withdrawal, publishing, contract, or other sensitive external action is enabled by provisioning.
