"""Canonical Jet Brain service catalog with evidence requirements."""
from __future__ import annotations

_SERVICES=(
("websites","Websites","web","website_artifact"),
("apps","Applications","software","app_artifact"),
("ai","AI systems","ai","ai_artifact"),
("automation","Automation","automation","automation_evidence"),
("marketing","Marketing","marketing","publication_evidence"),
("seo","SEO","seo","search_evidence"),
("social","Social media","social","publication_evidence"),
("video","Video production","video","verified_media"),
("design","Design","design","design_artifact"),
("commerce","Commerce","commerce","delivery_evidence"),
("data","Data analysis","data","analysis_artifact"),
("software","Software engineering","software","release_evidence"),
("it","IT services","it","service_evidence"),
("research","Research","research","research_evidence"),
)

def catalog():
    return [{"id":i,"name":n,"category":c,"deliverables":[d],"proof_required":True,"truth_rule":"OFFERED_IS_NOT_DELIVERED"} for i,n,c,d in _SERVICES]
