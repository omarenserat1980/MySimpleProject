"""Deterministic routing of missions to the minimum useful specialist set."""
from dataclasses import dataclass

SPECIALISTS={
    "marketing":("marketing","growth","content"),
    "commerce":("commerce","supply_chain"),
    "finance":("finance","investment"),
    "business":("business","revenue"),
    "social":("social","ngo","impact"),
    "political":("political","governance"),
    "economic":("economic","trade","macro"),
    "defense":("defense","security","resilience"),
    "intelligence":("intelligence","evidence","scenarios"),
}

KEYWORDS={
    "marketing":("marketing","تسويق","ads","advertising","brand","fundraising","عملاء","مبيعات"),
    "commerce":("amazon","ebay","temu","alibaba","dropship","دروب","متجر","منتج"),
    "finance":("finance","financial","investment","invest","استثمار","مالي","أسهم"),
    "business":("project","business","service","client","مشروع","خدمة","عميل","ربح"),
    "social":("charity","ngo","nonprofit","donation","fundraising","جمعية","خيري","تبرع","منظمة"),
    "political":("politics","policy","government","election","سياسة","حكومة","قانون"),
    "economic":("economy","inflation","trade","market","اقتصاد","تضخم","تجارة"),
    "defense":("defense","security","military","أمني","دفاع","عسكري"),
}

@dataclass(frozen=True)
class MissionRoute:
    mission:str
    specialists:tuple[str,...]
    reason:str

def route(mission:str)->MissionRoute:
    text=mission.lower().strip()
    if not text: raise ValueError("mission required")
    selected=[]
    for domain,words in KEYWORDS.items():
        if any(w in text for w in words):
            selected.append(domain)
    if not selected:
        selected=["intelligence"]
    return MissionRoute(mission,tuple(selected),"keyword-routed minimum specialist set")
