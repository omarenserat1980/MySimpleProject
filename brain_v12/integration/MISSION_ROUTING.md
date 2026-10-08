# Brain Mission Routing

Brain should not activate every specialist for every question.

The router selects the minimum useful specialist set from the mission, then the intelligence layer can request additional domains if evidence shows they are materially relevant.

Example:
- Amazon product investment -> commerce + finance.
- Charity fundraising -> social + marketing.
- Export opportunity -> commerce + economic + supply chain.
- Public-policy question -> political + economic + social.
- Security question -> defense + intelligence.

The routing layer is planning-only. It does not authorize external actions.
