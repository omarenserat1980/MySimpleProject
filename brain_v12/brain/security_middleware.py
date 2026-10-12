"""ASGI helpers for defensive Brain API hardening."""
from __future__ import annotations
from .security_hardening import SecurityHardener

def apply_security_headers(response) -> None:
    for key, value in SecurityHardener.security_headers().items():
        response.headers.setdefault(key, value)

def client_identity(request) -> str:
    auth = request.headers.get("authorization", "")
    if auth:
        return "auth:" + SecurityHardener.fingerprint_public(auth[:128])
    client = getattr(request, "client", None)
    host = getattr(client, "host", "unknown")
    return "peer:" + SecurityHardener.fingerprint_public(host)
