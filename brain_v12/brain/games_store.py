"""BRAIN Games commerce contract.

The catalog separates discoverability from distributability.
Commercial game sale is allowed only when distribution_rights == "VERIFIED"
and delivery_method is configured. This module never handles card data.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal

Rights = Literal["UNKNOWN", "VERIFIED", "EXPIRED", "REVOKED"]
Status = Literal["DISCOVERY", "PREORDER", "AVAILABLE", "UNAVAILABLE"]

@dataclass(frozen=True)
class GameOffer:
    id: str
    title: str
    platform: str
    currency: str
    price: float
    status: Status
    distribution_rights: Rights
    delivery_method: str | None = None
    official_url: str | None = None

    @property
    def sellable_by_brain(self) -> bool:
        return (
            self.distribution_rights == "VERIFIED"
            and self.status in {"PREORDER", "AVAILABLE"}
            and bool(self.delivery_method)
            and self.price >= 0
        )

    def public_record(self) -> dict:
        data = asdict(self)
        data["sellable_by_brain"] = self.sellable_by_brain
        return data

CATALOG: tuple[GameOffer, ...] = (
    GameOffer("control-resonant","CONTROL Resonant","PS5","USD",54.99,"AVAILABLE","UNKNOWN",None,
              "https://store.playstation.com/en-ae/product/EP5291-PPSA34547_00-0210080241603648"),
    GameOffer("ace-combat-8","ACE COMBAT 8: WINGS OF THEVE","PS5","USD",71.99,"AVAILABLE","UNKNOWN",None,
              "https://store.playstation.com/en-ae/concept/10011942"),
    GameOffer("gta-vi","Grand Theft Auto VI","PS5","USD",79.99,"PREORDER","UNKNOWN",None,
              "https://store.playstation.com/ar-ae/product/EP1004-PPSA01547_00-GTAVISTANDARD001"),
)

def catalog() -> list[dict]:
    return [item.public_record() for item in CATALOG]

def sellable_offers() -> list[dict]:
    return [item.public_record() for item in CATALOG if item.sellable_by_brain]
