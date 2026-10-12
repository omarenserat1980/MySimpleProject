# Brain Revenue Source Registry

Status: ACTIVE DESIGN — evidence-first, permission-gated

## Purpose

Brain continuously discovers lawful revenue paths that can be executed with minimal human mediation. Discovery is not revenue. A path becomes REVENUE_REALIZED only after independent payment evidence is available.

## Priority order

1. BRAIN_OWNED — products, games, APIs, tools, media and digital assets owned by Brain.
2. FREE_DIVERSE — open-source bounties, sponsorships, grants, legitimate task markets and free infrastructure.
3. PAID_EXTERNAL — paid providers only after verified company funds and explicit authorization.

## Revenue families

| Family | Example output | Automation potential | Initial cash cost |
|---|---|---:|---:|
| Open-source bounties | code, tests, docs, fixes | High | $0 target |
| GitHub Sponsors | maintained Brain projects | High after setup | $0 |
| Digital products | templates, scripts, datasets, guides | High | $0 target |
| Games | browser/mobile/desktop games | High | $0 target |
| API/Micro-SaaS | automated utility/API | High | $0 target |
| Media assets | videos, sound/image packs, stories | High | $0 target |
| AI demos/services | hosted tools and demos | High | $0 target |
| Research/data products | validated datasets/reports | Medium-High | $0 target |

## Candidate channels

### GitHub Sponsors
GitHub permits eligible open-source contributors and organizations in supported regions to receive sponsorships. Jordan is currently listed as a supported receiving region. Brain must treat eligibility/setup as a separate gate and never assume payment availability until verified.

### itch.io
Useful for Brain's game factory and digital creative products. itch.io supports paid/free releases and open revenue sharing. Brain must calculate the configured revenue share and payment-provider fees before recognizing expected net revenue.

### Gumroad
Useful for direct digital-product sales. Current direct-profile pricing is transaction-based rather than monthly; Brain must calculate fees before estimating net revenue.

### Hugging Face Spaces / ZeroGPU
Useful as a low-cost/free execution and discovery layer for AI demos. Free usage has quotas, so Brain must classify it as a constrained executor, not unlimited infrastructure.

## Opportunity scoring

score = expected_net_value × probability_of_success × evidence_quality ÷ (risk + cost + execution_complexity)

Risk score must never override legal, payment, security, or irreversible-action gates.

## Commercial state machine

MONETIZATION_PATH_DEFINED
→ CUSTOMER_VALIDATED
→ PAYMENT_VERIFIED
→ REVENUE_REALIZED
→ PROFIT_VERIFIED

Required evidence examples:

- product/release identifier
- buyer/customer evidence where applicable
- transaction/payment identifier
- amount and currency
- settlement status
- attributable costs
- timestamps
- source URL or API evidence
- audit record

## Autonomous operating loop

DISCOVER → DEDUPE → QUALIFY → SCORE → BUILD → TEST → PUBLISH/DELIVER → VERIFY → LEARN

External publication, applications, contracts, payments, withdrawals and other material side effects remain permission-gated.

## Anti-fraud / anti-self-deception rules

- Never count views, stars, downloads, leads, clicks, forecasts or invoices as revenue.
- Never count a successful CI workflow as commercial success.
- Never pay for a service merely to test a revenue hypothesis.
- Never auto-withdraw or move funds.
- Never bypass platform rules, identity checks, taxes, KYC/AML or legal restrictions.
- Never depend on a single marketplace or provider.
- Keep unsuccessful opportunities as evidence for future learning rather than deleting them.

## First execution wave

1. Open-source bounty discovery.
2. Brain-owned game prototypes and game-store packaging.
3. Brain-owned digital developer tools/templates.
4. Brain-owned API/Micro-SaaS candidates using free infrastructure.
5. GitHub Sponsors readiness for qualifying open-source Brain components.
6. AI demos/services using free constrained compute.
7. Continuous discovery of additional legitimate channels.

Success condition: at least one path reaches independently verified payment; otherwise the result remains an opportunity, not income.
