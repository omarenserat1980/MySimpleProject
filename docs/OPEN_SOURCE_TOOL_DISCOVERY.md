# Open-source tool discovery

Electronic Brain exposes a read-only discovery API backed by GitHub's public repository search.

## Endpoints

- `GET /api/open-source/status` — capabilities and safety defaults.
- `GET /api/open-source/tools?q=workflow&category=automation&language=Python&limit=10` — discover public repositories in a category.

Supported categories: `ai`, `automation`, `programming`, `databases`, `security`, `monitoring`, `mcp`, `devops`, `data`, and `media`. The `category` parameter is optional; without it, the registry preserves general search behavior. Categories guide GitHub search terms and do not certify suitability or safety.

The registry returns repositories only when GitHub supplies a recognized SPDX license identifier. A repository is a candidate, not a verified safe dependency. Results include the repository URL, license, language, stars, topics, and `security_review_required=true`.

## Safety boundary

- Discovery does not clone, install, import, or execute third-party code.
- No repository is enabled as a Brain plugin merely because it appears in search results.
- Review license compatibility, maintenance, dependency risks, supply-chain provenance, sandboxing, permissions, and resource requirements before integration.
- Search uses GitHub's public API and can be rate-limited. Successful results are cached in memory for five minutes.
- This is a discovery foundation, not a claim that every open-source project in the world has been indexed.

## Example

```sh
curl 'https://YOUR-BRAIN-HOST/api/open-source/tools?q=server&category=mcp&limit=10'
```
