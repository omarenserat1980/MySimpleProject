# BRAIN AI Marketing — Independent Review Scorecard

## Purpose
Evaluate the public marketing service without treating engineering success as commercial success.

## Reviewer groups
1. Ordinary customer
2. Marketing practitioner
3. Marketing manager
4. Marketing-agency/company owner

## Scores
Score each category 0–10 and record evidence.

| Category | Question |
|---|---|
| Clarity | Can a first-time visitor explain what BRAIN AI sells? |
| Value | Is the paid offer understandable and worth considering? |
| Trust | Are claims, pricing, trial and payment states transparent? |
| UX | Can a customer navigate signup, login and ordering without confusion? |
| Service quality | Are deliverables specific enough to judge? |
| Marketing quality | Does the site communicate a credible value proposition? |
| Manager readiness | Are strategy, execution, measurement and reporting clear? |
| Agency-owner confidence | Would an agency/owner buy, refer, or partner with the service? |
| Commercial readiness | Can a real customer actually complete the commercial journey? |
| Technical reliability | Do the public flows work end-to-end with evidence? |

## Mandatory break tests
- Try to start the trial twice with the same email.
- Try login with wrong credentials.
- Try expired-trial ordering.
- Try a paid order when checkout is not connected.
- Refresh/reopen the browser and verify account state.
- Inspect whether any page implies payment, delivery, publication, revenue, or success without evidence.
- Verify that the public site points to a real public API rather than a relative /api path on GitHub Pages.

## Launch gate
COMMERCIAL_READY requires:
PUBLIC_SITE_LIVE AND PUBLIC_API_LIVE AND AUTH_VERIFIED AND TRIAL_ENFORCED AND ORDER_FLOW_VERIFIED AND PAYMENT_CHECKOUT_LIVE AND PAYMENT_VERIFICATION_LIVE AND DELIVERY_PATH_VERIFIED AND EVIDENCE_GENERATED

Otherwise status must remain COMMERCIAL_LAUNCH_BLOCKED or the precise partial state.

## Integrity rule
Never fabricate reviewer scores, customer feedback, payment evidence, revenue, or delivery evidence. Simulated reviews must be labeled SIMULATED.
