"""Initial monetization catalog for Electronic Brain.

These are candidate offers, not evidence of customers or revenue. Actual
commercial state must be advanced only by verified evidence.
"""
from __future__ import annotations

from brain_v12.business.monetization_registry import MonetizationEntry


INITIAL_MONETIZATION_CATALOG = (
    MonetizationEntry(
        capability_id="mining-opportunity-intelligence",
        capability_name="Mining Opportunity Intelligence",
        offer="Evidence-backed mining economics and opportunity analysis report",
        target_customer="Mining operators and infrastructure buyers",
        acquisition_channel="Direct outreach and technical reports",
        delivery_evidence="Versioned analysis report plus market evidence",
        cost_model="Public-data collection and Brain compute",
    ),
    MonetizationEntry(
        capability_id="cinematic-factory",
        capability_name="Cinematic Factory",
        offer="Low-cost automated short-film production package",
        target_customer="Creators, small businesses, and media teams",
        acquisition_channel="Portfolio, direct outreach, and digital storefront",
        delivery_evidence="Verified media artifact and QC record",
        cost_model="Tracked compute, storage, and media-input costs",
    ),
    MonetizationEntry(
        capability_id="customer-portal-api",
        capability_name="Customer Portal/API",
        offer="Audited customer workflow and API automation",
        target_customer="Small businesses needing workflow automation",
        acquisition_channel="Direct outreach and service landing page",
        delivery_evidence="API test evidence and customer delivery record",
        cost_model="Tracked hosting, compute, and support costs",
    ),
    MonetizationEntry(
        capability_id="brain-automation-services",
        capability_name="Brain Automation Services",
        offer="Custom automation, QA, and GitHub workflow engineering",
        target_customer="Developers and small technology teams",
        acquisition_channel="Freelance marketplaces and direct outreach",
        delivery_evidence="Committed code, test evidence, and delivery artifact",
        cost_model="Tracked compute and delivery time",
    ),
    MonetizationEntry(
        capability_id="digital-commerce",
        capability_name="Digital Commerce",
        offer="Digital products and Brain-built automation assets",
        target_customer="Online buyers of software and digital services",
        acquisition_channel="Digital storefront and content marketing",
        delivery_evidence="Product artifact plus order/delivery evidence",
        cost_model="Tracked production, platform, and fulfillment costs",
    ),
)


def initial_catalog_records() -> list[dict]:
    return [entry.to_record() for entry in INITIAL_MONETIZATION_CATALOG]
