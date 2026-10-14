"""Evidence-first engineering proposal factory for Brain V12.

Turns a stated problem into a structured, testable engineering proposal. This
module does not execute arbitrary code, provision resources, alter secrets, or
deploy; those actions require their own authorized execution paths.
"""
from __future__ import annotations

from typing import Any


MISSION_TERMS = ("bitcoin", "btc", "sha256", "sha-256", "stratum", "mining", "التعدين", "بيتكوين")
CODE_TERMS = ("software", "code", "tool", "app", "application", "script", "برمج", "أداة", "تطبيق", "كود")


class EngineeringFactory:
    """Build actionable proposal contracts with explicit verification gates."""

    def propose(self, problem: str, *, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        statement = str(problem or "").strip()
        if not statement:
            return {"status": "BLOCKED", "error": "PROBLEM_STATEMENT_REQUIRED", "proposal": None}

        lowered = statement.casefold()
        mission_aligned = any(term in lowered for term in MISSION_TERMS)
        software_work = any(term in lowered for term in CODE_TERMS) or mission_aligned
        evidence_items = evidence if isinstance(evidence, list) else []
        steps = [
            {"stage": "OBSERVE", "action": "Read the current implementation, state, and latest test evidence", "exit_criterion": "Relevant source and current checks identified"},
            {"stage": "DIAGNOSE", "action": "Identify the nearest evidenced blocker and distinguish facts from assumptions", "exit_criterion": "Root cause or explicit evidence gap recorded"},
            {"stage": "PROPOSE", "action": "Compare at least one minimal fix with a fallback and record risks", "exit_criterion": "Chosen option has a reason, acceptance criteria, and rollback path"},
            {"stage": "BUILD", "action": "Create or update the smallest reusable software tool, node, contract, or application component", "exit_criterion": "Change is scoped, reviewable, and isolated from production"},
            {"stage": "TEST", "action": "Add focused regression tests and run relevant CI checks", "exit_criterion": "Test output is tied to the exact commit"},
            {"stage": "INTEGRATE", "action": "Connect the component through an explicit capability/tool contract", "exit_criterion": "Integration test proves the caller can discover and invoke it"},
            {"stage": "VERIFY", "action": "Read back the result and compare it with acceptance criteria", "exit_criterion": "Evidence supports each claimed outcome"},
            {"stage": "LEARN", "action": "Record the outcome, unresolved blockers, and next smallest step", "exit_criterion": "Append-only evidence record exists"},
        ]
        if mission_aligned:
            acceptance = [
                "Real SHA-256d/Stratum integration remains distinct from simulation",
                "Pool-side accepted-share evidence is independently sourced",
                "Payout and wallet receipt are verified separately",
                "Net profit subtracts all evidenced operating and pool costs",
                "No live mining, paid resource, secret change, or deployment without explicit approval",
            ]
            next_step = "Inspect current CI and source for a real, authorized Stratum worker and pool-side evidence provider; implement only the nearest missing contract."
        else:
            acceptance = [
                "Problem and expected outcome are explicit",
                "Regression tests cover the failure mode",
                "The component is discoverable through a declared tool/capability contract",
                "No consequential external action occurs without authorization",
            ]
            next_step = "Inspect the relevant source and tests, then implement the smallest reversible change."
        proposal = {
            "proposal_id": "engineering-factory-v1",
            "problem": statement,
            "status": "PROPOSAL_READY",
            "mission_aligned": mission_aligned,
            "work_type": "SOFTWARE_TOOL_OR_APPLICATION" if software_work else "ENGINEERING_INVESTIGATION",
            "steps": steps,
            "deliverables": [
                {"kind": "tool", "purpose": "A reusable, discoverable operation with typed inputs and outputs"},
                {"kind": "software_component", "purpose": "A small implementation with a clear owner and bounded responsibility"},
                {"kind": "contract", "purpose": "Explicit preconditions, permissions, failure states, and evidence fields"},
                {"kind": "tests", "purpose": "Unit, integration, negative-path, and regression coverage"},
                {"kind": "evidence", "purpose": "Commit-linked test results and read-back verification"},
            ],
            "acceptance_criteria": acceptance,
            "next_action": next_step,
            "evidence_received": len(evidence_items),
            "evidence_sufficient_for_completion": False,
            "execution_started": False,
            "approval_required_for": ["live mining", "paid resources", "secret changes", "fund movement", "production deployment"],
            "claims": {"software_created": False, "integration_verified": False, "real_mining_verified": False, "revenue_verified": False, "net_profit_verified": False},
        }
        return {"status": "COMPLETED", "proposal": proposal}
