# Electronic Brain — eBay Zero-Budget Opportunity Research

## Purpose
Analyze actual historical sold-item data exported by the user from eBay Product Research. The local analyzer ranks product candidates using observed sale rows, sold-price ranges, and optional sell-through fields supplied by the export. It is a research aid, not a guarantee of demand or profit.

## Zero-cost workflow
1. Sign in to eBay normally and check whether seller registration and payout onboarding are available for the user's real Jordan address and identity. Do not change country or provide an invented address to bypass restrictions.
2. If eligible, open Seller Hub → Research → Product Research. eBay says Product Research is free to sellers and offers historical sold-price, shipping, seller-count, trend, and sell-through information. Export the relevant report if the account exposes an export option; otherwise provide a CSV manually assembled from permitted account-visible data.
3. Save the CSV locally; do not paste passwords, API secrets, payment data, or identity documents into ChatGPT or commit them to Git.
4. Run the analyzer from the repository root:

   ```bash
   python -m brain_v12.business.ebay_opportunity_research path/to/product_research.csv --output ebay_report.json
   ```

5. Profit modeling is intentionally disabled unless all costs are supplied explicitly. Example (illustrative fee rate only; verify actual eBay fees first):

   ```bash
   python -m brain_v12.business.ebay_opportunity_research research.csv \
     --unit-cost 8 --fee-rate 0.13 --outbound-shipping 5 --packaging-cost 0.5 \
     --currency USD --output ebay_report.json
   ```

## Data and scoring rules
- Sold prices are parsed from the supplied export; item ID is the preferred grouping key, with normalized exact title as fallback.
- Sale-row counts describe only the supplied dataset and time period. They do not estimate future sales.
- Sell-through is only reported if a value was supplied by the export; it is never inferred from unrelated snapshots.
- The score is a transparent heuristic for review priority, not a probability or earnings forecast.
- Net profit is a simplified estimate only when item cost, fee rate, outbound shipping, and packaging cost are all provided. Actual fee basis, international fees, taxes, currency conversion, returns, shipping from Jordan, customs, and payout fees must be checked separately.

## Safety and authority
- No web scraping or eBay login automation is implemented.
- No listing creation, messages, purchases, paid subscriptions, inventory orders, money transfers, or account changes occur.
- Do not list or promise delivery until actual shipping options, cost, delivery time, customs obligations, returns, and payout eligibility are confirmed.
- eBay's public seller onboarding requires identity and payout-method verification. Jordan appearing in an international-fee classification does not itself prove that a specific Jordan-based account can complete seller onboarding or receive payouts. Confirm in the official onboarding flow before sourcing goods.
- Treat an opportunity as a lead only. Revenue is realized only after a completed sale and verifiable payout, net of actual costs and reversals.

## CSV template
A blank header template is available at `ebay_product_research_template.csv`. Fill it only with real values from an eBay Product Research export or manually collected permitted results; do not treat an empty template or invented sample values as market evidence. Then run:

```bash
python -m brain_v12.business.ebay_opportunity_research ebay_product_research_template.csv --output ebay_report.json
```

An empty template correctly returns `NO_DATA`; it does not create sample opportunities.
