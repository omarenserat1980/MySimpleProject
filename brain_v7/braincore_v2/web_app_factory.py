"""Web/app product factory planning layer."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class WebProduct:
    name: str
    rtl: bool
    pages: tuple[str, ...]
    api: bool
    database: bool
    responsive: bool


def plan_web_product(name: str, pages: list[str] | tuple[str, ...],
                     *, rtl: bool = True, api: bool = True,
                     database: bool = True, responsive: bool = True) -> WebProduct:
    if not name.strip():
        raise ValueError("name must not be empty")
    if not pages:
        raise ValueError("at least one page is required")
    return WebProduct(name.strip(), rtl, tuple(pages), api, database, responsive)


def architecture(product: WebProduct) -> dict:
    return {
        "frontend": ["HTML", "CSS", "JavaScript"],
        "backend": ["API"] if product.api else [],
        "database": ["database"] if product.database else [],
        "ui": {"rtl": product.rtl, "responsive": product.responsive},
        "pages": list(product.pages),
        "stages": ["design", "build", "integrate", "verify", "package"],
    }


def snapshot() -> dict:
    return {
        "web": True,
        "rtl": True,
        "responsive": True,
        "api": True,
        "database": True,
        "external_publish_requires_authorization": True,
    }
