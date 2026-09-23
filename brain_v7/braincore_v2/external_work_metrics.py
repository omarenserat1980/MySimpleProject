"""Evidence-based external-work metrics; no fabricated income."""
from __future__ import annotations
from typing import Any


def summarize(opportunities, orders, accounts) -> dict[str, Any]:
    opps = list(opportunities.values())
    ords = list(orders.values())
    paid = [o for o in ords if o.payment_verified]
    return {
        "accounts": len(accounts),
        "opportunities": len(opps),
        "qualified": sum(x.stage == "QUALIFIED" for x in opps),
        "orders": len(ords),
        "paid_orders": len(paid),
        "verified_revenue_jod": round(sum(x.agreed_amount_jod for x in paid), 2),
        "conversion_discovered_to_order": round(len(ords) / len(opps), 4) if opps else 0.0,
        "conversion_order_to_paid": round(len(paid) / len(ords), 4) if ords else 0.0,
    }
