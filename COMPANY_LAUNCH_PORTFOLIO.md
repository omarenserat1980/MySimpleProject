# Brain Company — Launch Portfolio

> Effective 2026-10-04. GitHub remains the source of truth.

## Launch policy
Projects are launched in two distinct states:
- **PRODUCT_LAUNCHED**: the software/capability is publicly usable and its release evidence passes.
- **COMMERCIAL_LAUNCHED**: a validated offer, customer evidence, delivery evidence, and verified payment evidence exist.
A green CI workflow alone never proves either state.

## Portfolio

| Project | Purpose | Current launch track | Gate |
|---|---|---|---|
| Brain AI Platform | Brain-native AI workspace, orchestration, memory, tools and self-healing | PRODUCT_FIRST | Release Gate + public UI verification |
| Brain Cloud / GitHub Cloud | Free control plane for bounded execution, evidence and recovery | PRODUCT_FIRST | Cloud verification + evidence index |
| Brain Windows | Brain-native Windows runtime and real-boot path | VERIFICATION_FIRST | Real-boot evidence before release |
| Cinematic Factory | Free/open-source movie creation, QC and delivery | PRODUCT_FIRST | Render → QC → FFmpeg → Master QC → final.mp4 |
| Brain Sync | Cross-device/runtime synchronization and evidence convergence | PRODUCT_FIRST | Sync runtime tests + evidence |
| Opportunity & Economic Engine | Discover opportunities, normalize offers and track verified outcomes | COMMERCIAL_FIRST | Offer → customer → payment → revenue → profit |
| Customer Hub | Customer communication, delivery and feedback lifecycle | COMMERCIAL_FIRST | Outbound transport + delivery evidence |
| Knowledge/Quran Layer | Evidence-aware knowledge and reasoning services | PRODUCT_FIRST | Registry/audit verification |

## Launch order

### Wave 1 — Foundation products
1. Brain AI Platform
2. Brain Cloud / GitHub Cloud
3. Brain Sync

### Wave 2 — Demonstrable products
4. Brain Windows
5. Cinematic Factory
6. Knowledge/Quran Layer

### Wave 3 — Revenue products
7. Opportunity & Economic Engine
8. Customer Hub

## Release gates
Before a project is marked PRODUCT_LAUNCHED:
1. Source and configuration are committed.
2. Relevant CI tests pass.
3. Independent verification passes.
4. Required evidence artifact exists and is non-empty.
5. Public entry point or release artifact is reachable when applicable.
6. No known critical blocker is silently ignored.

Before COMMERCIAL_LAUNCHED:
1. A concrete offer exists.
2. Customer/buyer evidence exists.
3. Delivery evidence exists.
4. Payment is independently verified.
5. Revenue is recorded only from verified payment evidence.
6. Costs are evidenced before profit is declared.

## Autonomy order
BRAIN_OWNED → FREE_DIVERSE → PAID_EXTERNAL.

Paid services are optional scaling only and require the existing commercial authorization/funding gates.

## Current rule
The Brain may prepare, test, package and publish product artifacts when the corresponding release gate passes. It must not fabricate customer, payment, revenue or profit evidence.

## Next execution cycle
- Run the unified release verification for the Wave 1 products.
- Collect evidence and classify each project as READY / BLOCKED / NEEDS_EVIDENCE.
- Repair bounded failures automatically where the existing Supervisor contract permits.
- Publish only projects whose release gate passes.
- Open commercial work only for capabilities that have a concrete offer and measurable demand path.
