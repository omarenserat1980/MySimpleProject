"""Marketing science curriculum and capability graph."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class MarketingDomain:
    id: str
    name: str
    prerequisites: tuple[str, ...]
    capabilities: tuple[str, ...]

DOMAINS = (
    MarketingDomain("strategy","Marketing Strategy",(),("segmentation","positioning","go_to_market","pricing")),
    MarketingDomain("consumer","Consumer Science",("strategy",),("behavior","psychology","decision_science","trust")),
    MarketingDomain("brand","Brand & Creative",("strategy","consumer"),("brand","messaging","storytelling","copywriting")),
    MarketingDomain("content","Content Marketing",("brand",),("content_strategy","editorial","distribution")),
    MarketingDomain("seo","SEO & Search",("content",),("keyword_research","technical_seo","authority")),
    MarketingDomain("paid","Performance Marketing",("strategy","consumer"),("campaigns","creative_testing","media_buying")),
    MarketingDomain("sales","Sales & CRM",("consumer",),("lead_generation","qualification","outreach","retention")),
    MarketingDomain("growth","Growth",("content","seo","paid","sales"),("acquisition","activation","retention","referral")),
    MarketingDomain("analytics","Marketing Analytics",("growth",),("attribution","cohorts","experiments","incrementality")),
    MarketingDomain("ai_marketing","AI Marketing",("analytics","growth"),("automation","personalization","agentic_marketing")),
    MarketingDomain("leadership","Marketing Leadership",("strategy","analytics","ai_marketing"),("portfolio","budgeting","governance","scaling")),
)

def curriculum() -> tuple[MarketingDomain, ...]:
    return DOMAINS

def domain_ids() -> tuple[str, ...]:
    return tuple(x.id for x in DOMAINS)
