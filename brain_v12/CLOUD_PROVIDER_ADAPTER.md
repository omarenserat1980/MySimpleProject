# Brain Cloud Provider Adapter — Piece 2

Status: initial read-only Azure adapter built; live provider query and cloud deployment not yet proven.

## Purpose

Collect a timestamped snapshot from an already authenticated Azure CLI session using read-only commands:
- az account show
- az vm list-usage --location REGION
- az vm list-skus --location REGION --all

It does not create, update, resize, start, stop, or delete resources.

## Deliberate unknowns

Quota is not the same as physical capacity. A listed SKU is not proof that a VM can be allocated now. This first adapter leaves RAM, storage, price, and free-tier eligibility unknown until trusted sources for those facts are added. Those unknowns must cause the Free Cloud Capacity Gate to block eligibility.

## Test

    PYTHONPATH=. python -m pytest -q brain_v12/tests/test_cloud_provider_adapter.py

The unit tests use a mocked CLI runner. They prove local parsing and safety behavior, not access to an Azure subscription or real free capacity.
