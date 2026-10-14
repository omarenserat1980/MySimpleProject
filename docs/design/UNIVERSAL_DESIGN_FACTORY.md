# Universal Design Factory

## Purpose
A single governed workflow for software, architecture, digital logic, hardware, physical design, simulation, security, verification, infrastructure, manufacturing, reliability, and future domains.

## Execution order
1. Discover repository and tools.
2. Define requirements and acceptance criteria.
3. Design architecture and component contracts.
4. Implement in an isolated branch.
5. Test with available tools.
6. Verify evidence and security.
7. Review, document, and propose a pull request.
8. Merge/deploy only through separately authorized gates.

Security and verification are cross-cutting, not final-only phases.

## Specialist prompts
The canonical prompt set lives in `prompts/universal_design_factory/`, numbered 00–15. Use `brain_v12.design_factory.task_router.route_task` to map task descriptions to relevant domains and `brain_v12.design_factory.plan.prepare_design_plan` to produce an evidence-aware plan. These helpers plan only; they do not invoke executors or claim that a specialist tool is available.

## Operating constraints
Zero-budget first, simulation first, Termux/Linux portability when applicable, least privilege, preserve legacy requirements, and no claims beyond evidence. No automatic merge, deployment, purchase, secret mutation, or physical manufacturing.

## Status vocabulary
PLANNED, DESIGNED, IMPLEMENTED, SIMULATED, TESTED, VERIFIED, BLOCKED, FAILED, HARDWARE_VERIFIED, MANUFACTURED_VERIFIED, REVENUE_VERIFIED. These statuses are not interchangeable.

## Completion
Prompt files being present only proves the prompt library exists. Runtime capability requires implemented adapters, tools, tests, and evidence for each domain.
