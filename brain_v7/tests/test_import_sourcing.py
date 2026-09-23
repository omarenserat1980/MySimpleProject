from brain_v7.braincore_v2.import_landed_cost import ImportQuote,calculate
from brain_v7.braincore_v2.sourcing_engine import SupplierQuote,rank_suppliers

def test_landed_cost_is_not_product_price():
    r=calculate(ImportQuote(product_value_jod=100,international_freight_jod=20,
                            customs_rate=.10,sales_tax_rate=.16,clearance_jod=5))
    assert r["landed_cost_jod"] > 100
    assert r["source_rates_required"] is True

def test_supplier_risk_is_visible():
    r=rank_suppliers([SupplierQuote("A",5,100,20,False,False)])
    assert "supplier_not_verified" in r[0]["risk_flags"]
