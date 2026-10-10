"""Minimal GitHub API header policy with explicit read-only anonymous fallback."""

def build_github_headers(token=None, require_token=True):
    if not token and require_token:
        raise ValueError("GITHUB_TOKEN_NOT_CONFIGURED")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
