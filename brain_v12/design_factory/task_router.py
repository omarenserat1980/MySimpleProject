"""Deterministic, explainable routing from task descriptions to specialist prompts."""
from __future__ import annotations
from .registry import load_registry

KEYWORDS = {
"discovery":("inventory","discover","existing files","capability audit"),
"requirements":("requirement","acceptance criteria","specification","spec"),
"architecture":("architecture","component map","system design"),
"detailed_design":("detailed design","interface contract","data flow"),
"software":("python","software","api","database","user interface","ui","code"),
"digital_logic":("rtl","verilog","systemverilog","sha-256","sha256","asic","digital logic","hardware"),
"physical_design":("physical design","openroad","place and route","gdsii","timing closure","pdk"),
"simulation":("simulation","simulator","digital twin","virtual node"),
"security":("security","secret","threat","permission","safety"),
"verification":("verify","verification","validation","test","evidence","proof"),
"infrastructure":("infrastructure","deployment","deploy","ci","workflow","operations","runtime"),
"manufacturing":("manufacturing","fabrication","assembly","bom"),
"reliability":("reliability","recovery","self-healing","self healing","evolution","rollback"),
"integration":("integration","release","final acceptance","merge"),
"new_domain":("new domain","unlisted domain","new specialty")}
PROMPT_FOR_DOMAIN={"discovery":"01","requirements":"02","architecture":"03","detailed_design":"04","software":"05","digital_logic":"06","physical_design":"07","simulation":"08","security":"09","verification":"10","infrastructure":"11","manufacturing":"12","reliability":"13","integration":"14","new_domain":"15"}

def route_task(description: str) -> dict:
    """Return matched domains and prompt IDs; always include master and verification."""
    if not isinstance(description,str) or not description.strip():
        raise ValueError("description must be a non-empty string")
    text=description.casefold()
    matches=[domain for domain,terms in KEYWORDS.items() if any(term in text for term in terms)]
    if not matches: matches=["new_domain"]
    if "physical_design" in matches and "digital_logic" not in matches: matches.append("digital_logic")
    prompt_ids=["00"]
    for domain in matches:
        prompt_id=PROMPT_FOR_DOMAIN.get(domain)
        if prompt_id and prompt_id not in prompt_ids: prompt_ids.append(prompt_id)
    if "10" not in prompt_ids: prompt_ids.append("10")
    registry_ids={item["id"] for item in load_registry()["prompts"]}
    return {"domains":matches,"prompt_ids":[p for p in prompt_ids if p in registry_ids],"review_required":True}
