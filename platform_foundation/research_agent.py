from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from time import time
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class ResearchEvidence:
    evidence_id: str
    query: str
    title: str
    url: str
    excerpt: str
    source: str
    confidence: float
    retrieved_at: float
    content_hash: str


@dataclass(frozen=True)
class ResearchReport:
    query: str
    evidence: tuple[ResearchEvidence, ...]
    unique_sources: int
    confidence: float


class ResearchAgent:
    """Evidence-first web/research adapter.

    Network access is injected by the caller. The agent stores provenance,
    normalizes URLs, deduplicates evidence, and never treats empty results
    as successful research.
    """

    KEY = "platform.research.evidence"

    def __init__(self, store: SQLiteStateStore, *, fetch: Callable[[str], Iterable[dict[str, Any]]] | None = None):
        self.store = store
        self.fetch = fetch

    @staticmethod
    def _url(url: str) -> str:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("source URL is required")
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("only HTTP(S) source URLs are allowed")
        return parsed._replace(fragment="").geturl()

    @staticmethod
    def _query(query: str) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("research query is required")
        return re.sub(r"\s+", " ", query.strip())[:512]

    def ingest(self, *, query: str, results: Iterable[dict[str, Any]]) -> ResearchReport:
        query = self._query(query)
        records = dict(self.store.get(self.KEY, {}))
        evidence: list[ResearchEvidence] = []
        seen: set[str] = set()
        for item in results:
            url = self._url(str(item.get("url", "")))
            title = str(item.get("title", "")).strip()
            excerpt = str(item.get("excerpt", "")).strip()
            source = str(item.get("source", "")).strip() or urlparse(url).netloc
            confidence = float(item.get("confidence", 0.0))
            if not title or not excerpt:
                continue
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("confidence must be between 0 and 1")
            digest = hashlib.sha256((url + "\n" + title + "\n" + excerpt).encode()).hexdigest()
            if digest in seen or digest in records:
                continue
            seen.add(digest)
            evidence.append(ResearchEvidence(
                evidence_id=digest, query=query, title=title, url=url,
                excerpt=excerpt[:4000], source=source[:256],
                confidence=confidence, retrieved_at=time(), content_hash=digest,
            ))
        for item in evidence:
            records[item.evidence_id] = asdict(item)
        self.store.set(self.KEY, records)
        confidence = (sum(item.confidence for item in evidence) / len(evidence)) if evidence else 0.0
        return ResearchReport(query, tuple(evidence), len({item.url for item in evidence}), confidence)

    def search(self, query: str) -> ResearchReport:
        if self.fetch is None:
            raise RuntimeError("no research source adapter configured")
        return self.ingest(query=query, results=self.fetch(self._query(query)))

    def evidence(self, query: str | None = None) -> list[ResearchEvidence]:
        items = [ResearchEvidence(**item) for item in self.store.get(self.KEY, {}).values()]
        if query is not None:
            query = self._query(query)
            items = [item for item in items if item.query == query]
        return sorted(items, key=lambda item: item.retrieved_at)

    def is_ready(self) -> bool:
        return self.store.is_ready()


__all__ = ["ResearchAgent", "ResearchEvidence", "ResearchReport"]
