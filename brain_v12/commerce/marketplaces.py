"""Marketplace capability matrix; no automatic account actions."""
from dataclasses import dataclass
from .commerce_engine import Channel

@dataclass(frozen=True)
class MarketplacePolicy:
    channel:Channel
    listing_requires_authorization:bool=True
    purchase_requires_authorization:bool=True
    payout_requires_verified_account:bool=True
    external_side_effects:bool=True

POLICIES={c:MarketplacePolicy(c) for c in Channel}
