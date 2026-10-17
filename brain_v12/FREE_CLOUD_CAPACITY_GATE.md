# Brain Free Cloud Capacity Gate — Piece 1

Status: **built as a local decision component; not connected to a provider and not deployed**.

## Purpose

Before Brain creates or uses a cloud resource, it must prove that the selected
provider/region/SKU has enough capacity and that the estimated cost is exactly
USD 0. This component is read-only: it does not create, delete, resize, or start
cloud resources, and it never falls back to a paid option.

## Files

- brain_v12/brain/cloud_capacity_gate.py — fail-closed eligibility evaluator.
- brain_v12/tests/test_cloud_capacity_gate.py — safety and behavior tests.

## Evidence contract

A provider adapter must authenticate its provider response and pass:
provider_verified, provider, region, sku, source_ref, observed_at, expires_at,
free_tier_eligible, estimated_monthly_cost_usd, available_vcpu,
available_memory_mb, and available_storage_gb.

Manually written evidence must never be marked provider-verified. Missing,
stale, malformed, insufficient, unverified, or non-zero-cost evidence blocks
eligibility. The test fixture is synthetic and is not evidence of actual free
cloud capacity.

## Verification

Run from repository root:

    python -m pytest brain_v12/tests/test_cloud_capacity_gate.py -q

Passing unit tests proves the gate's local logic only. It does not prove that
Azure or another provider offers free capacity, that a cloud VM exists, or that
Windows Server 2025 boots. Provider discovery, free-cost verification, and a
real task with independent evidence remain separate gates.
