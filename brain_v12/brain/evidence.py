from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib, json, time, uuid
from typing import Any

class EvidenceStatus(str, Enum):
    OBSERVED = "OBSERVED"
    VERIFIED = "VERIFIED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"

@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    issuer: str
    actor: str
    provider_id: str
    component_id: str
    resource_ids: tuple[str, ...]
    method: str
    source: str
    measurement: dict[str, Any]
    observed_at: float
    expires_at: float | None
    confidence: float
    digest: str
    status: EvidenceStatus = EvidenceStatus.OBSERVED

    @staticmethod
    def create(*, issuer: str, actor: str, provider_id: str, component_id: str,
               resource_ids: list[str], method: str, source: str,
               measurement: dict[str, Any], confidence: float = 1.0,
               ttl_seconds: int | None = None) -> "EvidenceRecord":
        now = time.time()
        if not issuer or not actor or not provider_id or not component_id:
            raise ValueError("EVIDENCE_IDENTITY_REQUIRED")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("EVIDENCE_CONFIDENCE_INVALID")
        payload = {"issuer": issuer, "actor": actor, "provider_id": provider_id,
                   "component_id": component_id, "resource_ids": sorted(resource_ids),
                   "method": method, "source": source, "measurement": measurement,
                   "observed_at": now}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return EvidenceRecord(f"ev-{uuid.uuid4().hex[:16]}", issuer, actor, provider_id,
                              component_id, tuple(sorted(resource_ids)), method, source,
                              dict(measurement), now, now + ttl_seconds if ttl_seconds else None,
                              confidence, digest, EvidenceStatus.VERIFIED)

    def valid(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return self.status == EvidenceStatus.VERIFIED and (self.expires_at is None or self.expires_at > now)

    def public(self) -> dict[str, Any]:
        x = asdict(self)
        x["resource_ids"] = list(self.resource_ids)
        x["status"] = self.status.value
        return x

class EvidenceStore:
    def __init__(self):
        self.records: dict[str, EvidenceRecord] = {}

    def put(self, record: EvidenceRecord) -> EvidenceRecord:
        old = self.records.get(record.evidence_id)
        if old and old.digest != record.digest:
            raise RuntimeError("EVIDENCE_ID_REUSE")
        self.records[record.evidence_id] = record
        return record

    def get_valid(self, evidence_id: str, component_id: str | None = None,
                  resource_ids: list[str] | None = None) -> EvidenceRecord:
        record = self.records.get(evidence_id)
        if record is None or not record.valid():
            raise RuntimeError("EVIDENCE_NOT_VALID")
        if component_id and record.component_id != component_id:
            raise RuntimeError("EVIDENCE_COMPONENT_MISMATCH")
        if resource_ids and not set(resource_ids).issubset(record.resource_ids):
            raise RuntimeError("EVIDENCE_RESOURCE_MISMATCH")
        return record

    def revoke(self, evidence_id: str) -> None:
        record = self.records.get(evidence_id)
        if record is None:
            raise KeyError("EVIDENCE_NOT_FOUND")
        self.records[evidence_id] = EvidenceRecord(*record.__match_args__) if False else EvidenceRecord(
            record.evidence_id, record.issuer, record.actor, record.provider_id,
            record.component_id, record.resource_ids, record.method, record.source,
            record.measurement, record.observed_at, record.expires_at, record.confidence,
            record.digest, EvidenceStatus.REVOKED)

    def inspect(self) -> dict[str, Any]:
        now = time.time()
        return {"count": len(self.records),
                "valid": sum(r.valid(now) for r in self.records.values()),
                "records": [r.public() for r in self.records.values()]}
