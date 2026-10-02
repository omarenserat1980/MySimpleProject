"""Evidence gate for company media content."""
from __future__ import annotations

def validate(content: str, brand: dict) -> dict:
    text = content.strip()
    checks = {
        "non_empty": bool(text),
        "no_prohibited_claims": not any(
            p.lower() in text.lower() for p in brand.get("prohibited_claims", [])
        ),
        "has_company_context": any(
            x.lower() in text.lower()
            for x in [brand.get("company_name", "")] + brand.get("products", [])
            if x
        ),
    }
    return {"ok": all(checks.values()), "checks": checks}
