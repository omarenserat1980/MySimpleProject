from __future__ import annotations
from .auth import TokenRecord, issue_token, verify_token

class TokenAuthority:
    def __init__(self):
        self._records: dict[str, TokenRecord] = {}

    def issue(self, subject: str, scopes: set[str]) -> str:
        raw, record = issue_token(subject, scopes)
        self._records[record.token_hash] = record
        return raw

    def verify(self, raw: str, required_scope: str) -> bool:
        import hashlib
        digest=hashlib.sha256(raw.encode()).hexdigest()
        record=self._records.get(digest)
        return bool(record and verify_token(raw, record, required_scope))
