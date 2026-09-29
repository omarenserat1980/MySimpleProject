from __future__ import annotations
import hashlib, hmac, secrets
from dataclasses import dataclass

@dataclass(frozen=True)
class TokenRecord:
    token_hash: str
    subject: str
    scopes: frozenset[str]

def issue_token(subject: str, scopes: set[str]) -> tuple[str, TokenRecord]:
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, TokenRecord(digest, subject, frozenset(scopes))

def verify_token(raw: str, record: TokenRecord, required_scope: str) -> bool:
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return hmac.compare_digest(digest, record.token_hash) and required_scope in record.scopes
