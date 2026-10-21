"""Zero-cost, evidence-first analyzer for seller-exported eBay Product Research CSVs.

This module never scrapes eBay, logs in, creates listings, buys inventory, or places orders.
It analyzes a CSV exported by the user from eBay Product Research and labels coverage limits.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ALIASES = {
    "title": ("title", "item title", "product title", "listing title", "name"),
    "item_id": ("item id", "item number", "listing id", "ebay item id"),
    "sold_price": ("sold price", "sold for", "price sold", "sale price", "item price", "price"),
    "shipping": ("shipping", "shipping cost", "postage", "delivery cost"),
    "sold_date": ("sold date", "date sold", "sale date", "end date", "date"),
    "quantity": ("quantity sold", "sold quantity", "quantity", "qty"),
    "active_listings": ("active listings", "active listing count", "current listings"),
    "sell_through_rate": ("sell-through rate", "sell through rate", "sell-through", "sell through"),
    "seller_count": ("number of sellers", "sellers", "seller count", "unique sellers"),
    "source_url": ("url", "item url", "listing url", "source url"),
}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def _number(value: Any) -> float | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.replace(",", "").replace("\u00a0", " ")
    match = re.search(r"-?\d+(?:\.\d+)?", raw.replace("$", "").replace("£", "").replace("€", ""))
    if not match:
        return None
    try:
        result = float(match.group(0))
        return result if result >= 0 else None
    except ValueError:
        return None


def _headers(fieldnames: list[str] | None) -> dict[str, str]:
    found: dict[str, str] = {}
    for original in fieldnames or []:
        normalized = _key(original)
        for target, variants in ALIASES.items():
            if normalized in {_key(v) for v in variants} and target not in found:
                found[target] = original
    return found


def _parse_date(value: Any) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y", "%d %b %Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def analyze_rows(
    rows: list[dict[str, Any]],
    *,
    unit_cost: float | None = None,
    fee_rate: float | None = None,
    outbound_shipping: float | None = None,
    packaging_cost: float | None = None,
    currency: str = "USD",
) -> dict[str, Any]:
    """Aggregate actual sold rows. Profit is shown only when all cost inputs are supplied."""
    if not rows:
        return {"schema_version": 1, "status": "NO_DATA", "row_count": 0, "opportunities": [],
                "limitations": ["No sold-item rows were supplied."]}
    columns = _headers(list(rows[0].keys()))
    if "sold_price" not in columns:
        raise ValueError("CSV must contain a sold-price column from eBay Product Research.")
    if "title" not in columns and "item_id" not in columns:
        raise ValueError("CSV must contain an item title or item ID column for grouping.")
    if fee_rate is not None and not 0 <= fee_rate < 1:
        raise ValueError("fee_rate must be a fraction between 0 and 1, such as 0.13 for 13%.")
    for name, value in (("unit_cost", unit_cost), ("outbound_shipping", outbound_shipping), ("packaging_cost", packaging_cost)):
        if value is not None and value < 0:
            raise ValueError(f"{name} cannot be negative.")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped = 0
    for row in rows:
        title = str(row.get(columns.get("title", ""), "")).strip()
        item_id = str(row.get(columns.get("item_id", ""), "")).strip()
        price = _number(row.get(columns["sold_price"]))
        if price is None or (not title and not item_id):
            skipped += 1
            continue
        # Prefer item ID when present; otherwise exact normalized title. Never fuzzy-merge distinct titles.
        group_key = f"id:{item_id}" if item_id else f"title:{_key(title)}"
        shipping = _number(row.get(columns.get("shipping", ""))) if "shipping" in columns else None
        qty = _number(row.get(columns.get("quantity", ""))) if "quantity" in columns else None
        active = _number(row.get(columns.get("active_listings", ""))) if "active_listings" in columns else None
        sell_through = _number(row.get(columns.get("sell_through_rate", ""))) if "sell_through_rate" in columns else None
        sellers = _number(row.get(columns.get("seller_count", ""))) if "seller_count" in columns else None
        groups[group_key].append({
            "title": title or f"eBay item {item_id}", "item_id": item_id or None,
            "sold_price": price, "shipping": shipping,
            "sold_date": _parse_date(row.get(columns.get("sold_date", ""))) if "sold_date" in columns else None,
            "quantity": qty, "active_listings": active,
            "sell_through_rate": sell_through, "seller_count": sellers,
            "source_url": str(row.get(columns.get("source_url", ""), "")).strip() or None,
        })

    opportunities = []
    for group_key, sales in groups.items():
        prices = [s["sold_price"] for s in sales]
        shipping_values = [s["shipping"] for s in sales if s["shipping"] is not None]
        dates = [s["sold_date"] for s in sales if s["sold_date"]]
        title = sales[0]["title"]
        observed_sold_units = sum((s["quantity"] if s["quantity"] is not None else 1) for s in sales)
        # The export's sell-through value is used only if explicitly supplied; never fabricate it.
        supplied_str = [s["sell_through_rate"] for s in sales if s["sell_through_rate"] is not None]
        supplied_active = [s["active_listings"] for s in sales if s["active_listings"] is not None]
        supplied_sellers = [s["seller_count"] for s in sales if s["seller_count"] is not None]
        typical_shipping = statistics.median(shipping_values) if shipping_values else None
        profit_inputs_complete = all(v is not None for v in (unit_cost, fee_rate, outbound_shipping, packaging_cost))
        median_price = statistics.median(prices)
        net_profit = None
        margin_pct = None
        if profit_inputs_complete:
            # fee is modeled against item price only; actual eBay fees depend on marketplace/category and fee basis.
            modeled_fee = median_price * float(fee_rate)
            net_profit = median_price - float(unit_cost) - modeled_fee - float(outbound_shipping) - float(packaging_cost)
            margin_pct = (net_profit / median_price * 100) if median_price > 0 else None
        # Transparent heuristic only; it is not a sales forecast.
        score = min(50, len(sales) * 5)
        if len(dates) >= 2 and (max(dates) != min(dates)):
            score += 10
        if supplied_str:
            score += min(20, max(0, int(statistics.median(supplied_str))))
        if profit_inputs_complete and net_profit is not None and net_profit > 0:
            score += 20
        opportunities.append({
            "group_key": group_key, "title": title, "item_id": sales[0]["item_id"],
            "observed_sale_rows": len(sales), "observed_units_sold": observed_sold_units,
            "median_sold_price": round(median_price, 2), "mean_sold_price": round(statistics.mean(prices), 2),
            "min_sold_price": round(min(prices), 2), "max_sold_price": round(max(prices), 2),
            "median_buyer_shipping": round(typical_shipping, 2) if typical_shipping is not None else None,
            "first_observed_sale_date": min(dates) if dates else None,
            "last_observed_sale_date": max(dates) if dates else None,
            "sell_through_rate_source_value": round(statistics.median(supplied_str), 2) if supplied_str else None,
            "active_listing_count_source_value": int(statistics.median(supplied_active)) if supplied_active else None,
            "seller_count_source_value": int(statistics.median(supplied_sellers)) if supplied_sellers else None,
            "modeled_fee_rate": fee_rate, "modeled_net_profit_per_unit": round(net_profit, 2) if net_profit is not None else None,
            "modeled_margin_percent": round(margin_pct, 2) if margin_pct is not None else None,
            "currency": currency, "research_score": score,
            "score_is_heuristic_not_forecast": True,
            "evidence_urls": sorted({s["source_url"] for s in sales if s["source_url"]}),
        })
    opportunities.sort(key=lambda x: (x["research_score"], x["observed_sale_rows"], x["median_sold_price"]), reverse=True)
    limitations = [
        "Results describe only the rows and time window in the supplied export; they are not a complete-market census.",
        "Observed sold listings are evidence of past sales, not a guarantee of future demand or profit.",
        "No scraping, account login, listing creation, purchases, messages, or orders were performed.",
        "Profit is omitted unless unit cost, fee rate, outbound shipping, and packaging cost are all supplied.",
        "The fee model is simplified; verify the actual marketplace, category, international, payment, tax, and return costs before any decision.",
    ]
    if skipped:
        limitations.append(f"Skipped {skipped} row(s) with missing title/item ID or unparseable sold price.")
    if not any(x["sell_through_rate_source_value"] is not None for x in opportunities):
        limitations.append("Sell-through rate was not present in the input, so it was not estimated.")
    return {"schema_version": 1, "status": "ANALYZED" if opportunities else "NO_VALID_ROWS",
            "currency": currency, "row_count": len(rows), "valid_sale_rows": sum(len(v) for v in groups.values()),
            "unique_groups": len(opportunities), "skipped_rows": skipped,
            "profit_model_enabled": all(v is not None for v in (unit_cost, fee_rate, outbound_shipping, packaging_cost)),
            "opportunities": opportunities, "limitations": limitations,
            "side_effects": {"network_access": False, "listing_created": False, "purchase_made": False,
                             "message_sent": False, "money_moved": False}}


def analyze_csv(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    with open(path, "r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        return analyze_rows(list(reader), **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="CSV exported from eBay Product Research")
    parser.add_argument("--output", help="Optional JSON output path; otherwise prints to stdout")
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--unit-cost", type=float)
    parser.add_argument("--fee-rate", type=float, help="Fraction, e.g. 0.13 for 13%%; verify actual fee schedule")
    parser.add_argument("--outbound-shipping", type=float)
    parser.add_argument("--packaging-cost", type=float)
    args = parser.parse_args()
    report = analyze_csv(args.input, unit_cost=args.unit_cost, fee_rate=args.fee_rate,
                         outbound_shipping=args.outbound_shipping, packaging_cost=args.packaging_cost,
                         currency=args.currency)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
