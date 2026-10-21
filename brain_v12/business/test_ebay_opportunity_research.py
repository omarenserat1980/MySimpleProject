from __future__ import annotations

import pytest
import subprocess
import sys

from brain_v12.business.ebay_opportunity_research import analyze_rows


def test_aggregates_observed_sold_prices_and_never_invents_sell_through():
    report = analyze_rows([
        {"Item title": "Used Camera X", "Sold price": "$100.00", "Sold date": "2026-10-01", "Shipping cost": "$8.00"},
        {"Item title": "Used Camera X", "Sold price": "$120.00", "Sold date": "2026-10-10", "Shipping cost": "$10.00"},
        {"Item title": "Used Camera Y", "Sold price": "$30.00", "Sold date": "2026-10-11"},
    ])
    assert report["status"] == "ANALYZED"
    first = report["opportunities"][0]
    assert first["title"] == "Used Camera X"
    assert first["observed_sale_rows"] == 2
    assert first["median_sold_price"] == 110.0
    assert first["median_buyer_shipping"] == 9.0
    assert first["sell_through_rate_source_value"] is None
    assert first["modeled_net_profit_per_unit"] is None
    assert report["side_effects"]["purchase_made"] is False


def test_profit_requires_all_explicit_cost_inputs():
    report = analyze_rows(
        [{"title": "Product A", "sold price": "50"}],
        unit_cost=20, fee_rate=0.1, outbound_shipping=5, packaging_cost=1,
    )
    item = report["opportunities"][0]
    assert item["modeled_net_profit_per_unit"] == 19.0
    assert item["modeled_margin_percent"] == 38.0
    assert report["profit_model_enabled"] is True


def test_skips_bad_prices_and_requires_sold_price_header():
    report = analyze_rows([
        {"title": "Bad row", "sold price": "not available"},
        {"title": "Good row", "sold price": "12.50"},
    ])
    assert report["skipped_rows"] == 1
    assert report["valid_sale_rows"] == 1
    with pytest.raises(ValueError, match="sold-price"):
        analyze_rows([{"title": "Missing price", "views": "200"}])


def test_uses_item_id_as_grouping_key_when_present():
    report = analyze_rows([
        {"title": "Different title 1", "item id": "123", "sold price": "10"},
        {"title": "Different title 2", "item id": "123", "sold price": "12"},
    ])
    assert report["unique_groups"] == 1
    assert report["opportunities"][0]["group_key"] == "id:123"


def test_cli_missing_input_shows_actionable_error():
    result = subprocess.run(
        [sys.executable, "-m", "brain_v12.business.ebay_opportunity_research",
         "/path/to/product_research.csv"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "CSV file not found" in result.stderr
    assert "Replace /path/to/product_research.csv" in result.stderr
