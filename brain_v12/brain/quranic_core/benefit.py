from __future__ import annotations

class HumanBenefitEngine:
    """Converts validated findings into safe project directions, not religious rulings."""
    def propose(self, finding: str, domains: list[str] | None = None) -> dict:
        domains = domains or ["education", "research", "social_good", "accessibility"]
        return {
            "finding": finding,
            "domains": domains,
            "principles": [
                "serve people without manipulation",
                "respect dignity and consent",
                "measure real-world benefit",
                "avoid presenting Brain output as revelation",
                "require human review for consequential actions",
            ],
            "status": "IDEAS_ONLY",
        }
