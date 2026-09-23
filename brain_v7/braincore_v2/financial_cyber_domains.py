"""Financial, banking and defensive cybersecurity capability registry.

Covers legitimate engineering knowledge: payment rails, bank integrations,
card/ATM security, fraud controls, reconciliation, and defensive security.
It intentionally excludes credential theft, card cloning, unauthorized access,
malware deployment, or bypassing bank controls.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Domain:
    name:str
    category:str
    sensitivity:str
    evidence_required:bool=True

DOMAINS=(
    Domain("banking_systems","banking","high"),
    Domain("payment_rails","payments","high"),
    Domain("card_processing","cards","high"),
    Domain("atm_security","atm","high"),
    Domain("payment_reconciliation","finance","high"),
    Domain("fraud_detection","risk","high"),
    Domain("financial_accounting","finance","medium"),
    Domain("fintech_api_engineering","software","high"),
    Domain("cryptography","cybersecurity","high"),
    Domain("defensive_security","cybersecurity","high"),
    Domain("incident_response","cybersecurity","high"),
    Domain("application_security","cybersecurity","high"),
    Domain("pci_dss_concepts","compliance","high"),
    Domain("aml_kyc_concepts","compliance","high"),
)

FORBIDDEN_ACTIONS={
    "steal_credentials","clone_card","skim_card","bypass_atm_security",
    "unauthorized_bank_access","steal_funds","deploy_malware",
}

def capability_map()->list[dict]:
    return [{"name":d.name,"category":d.category,"sensitivity":d.sensitivity,
             "evidence_required":d.evidence_required} for d in DOMAINS]

def action_allowed(action:str)->bool:
    return action not in FORBIDDEN_ACTIONS
