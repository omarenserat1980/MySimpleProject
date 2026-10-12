#!/usr/bin/env python3
"""Read-only Azure Retail Prices estimate for Windows VM compute.

This does not authenticate to Azure or create resources. It deliberately labels
the result as compute-only: disks, public IP, bandwidth, taxes, and subscription
credits/free-service eligibility must be checked separately before deployment.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://prices.azure.com/api/retail/prices"
CANDIDATE_SKUS = ("Standard_B1s", "Standard_B2s")


def fetch_windows_hourly_price(region: str, sku: str) -> dict:
    filters = (
        "serviceName eq 'Virtual Machines' "
        f"and armRegionName eq '{region}' "
        f"and armSkuName eq '{sku}' "
        "and priceType eq 'Consumption'"
    )
    url = API + "?" + urlencode({"$filter": filters})
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "ElectronicBrain-CostPreflight/1.0"})
    with urlopen(request, timeout=25) as response:
        payload = json.load(response)

    items = payload.get("Items", payload.get("items", []))
    candidates = []
    for item in items:
        product = str(item.get("productName", ""))
        meter = str(item.get("meterName", ""))
        unit = str(item.get("unitOfMeasure", ""))
        if "windows" not in product.lower():
            continue
        if unit.lower() not in {"1 hour", "1 hours"}:
            continue
        if any(tag in meter.lower() for tag in ("spot", "low priority", "low-priority")):
            continue
        try:
            price = float(item.get("retailPrice", item.get("unitPrice")))
        except (TypeError, ValueError):
            continue
        candidates.append({
            "sku": sku,
            "region": region,
            "currency": item.get("currencyCode", "USD"),
            "hourly_compute": price,
            "estimated_730_hour_compute": round(price * 730, 2),
            "meter_name": meter,
            "product_name": product,
            "unit": unit,
            "price_effective_date": item.get("effectiveStartDate"),
            "source": API,
        })
    if not candidates:
        raise RuntimeError(f"No unambiguous Windows hourly consumption price found for {sku} in {region}")
    # The standard hourly Windows meter is normally unique; if the API returns
    # several, prefer the exact meter name and otherwise refuse to silently pick.
    exact = [row for row in candidates if row["meter_name"].replace(" ", "").lower() == sku.replace("Standard_", "").replace("_", "").lower()]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    prices = {(row["currency"], row["hourly_compute"], row["meter_name"]) for row in candidates}
    if len(prices) == 1:
        return candidates[0]
    raise RuntimeError(f"Multiple Windows price meters found for {sku}; manual review is required")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="westeurope")
    parser.add_argument("--output", default="windows-cloud-cost-estimate.json")
    args = parser.parse_args()

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "region": args.region,
        "source": API,
        "status": "PRICE_LOOKUP_PENDING",
        "vm_estimates": [],
        "scope": "COMPUTE_ONLY",
        "not_included": [
            "managed OS disk and any extra disks",
            "public IPv4 address and network egress",
            "taxes, negotiated discounts, and exchange rates",
            "subscription-specific free credits or free-service eligibility",
        ],
        "safety": {
            "azure_authenticated": False,
            "resources_created_or_changed": False,
            "apply_authorized": False,
        },
        "next_gate": "Review the complete Azure Pricing Calculator estimate and subscription free-benefit eligibility before any apply.",
    }
    errors = []
    for sku in CANDIDATE_SKUS:
        try:
            report["vm_estimates"].append(fetch_windows_hourly_price(args.region, sku))
        except Exception as exc:
            errors.append(f"{sku}: {type(exc).__name__}: {exc}")
    report["errors"] = errors
    report["status"] = "PRICE_LOOKUP_PASS" if len(report["vm_estimates"]) == len(CANDIDATE_SKUS) else "PRICE_LOOKUP_INCOMPLETE"
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PRICE_LOOKUP_PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
