"""Minimal Customer Portal API for the Electronic Brain.

The API is transport-neutral: customer submissions become durable lead records,
while marketing campaigns remain governed by the approval lifecycle.
No external message is sent by this module.
"""

from __future__ import annotations

import hashlib

from .customer_cases import CustomerCaseStore
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class LeadIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    service: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=10000)
    marketing_consent: bool = False


class LeadOut(LeadIn):
    id: int
    created_at: str
    content_hash: str
    status: str


class LeadStore:
    def __init__(self, path: str | Path = "data/customer_portal.db") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              email TEXT NOT NULL,
              service TEXT NOT NULL,
              details TEXT NOT NULL,
              marketing_consent INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              status TEXT NOT NULL
            )
            """
        )
        self.db.commit()

    def create(self, lead: LeadIn) -> LeadOut:
        created = datetime.now(timezone.utc).isoformat()
        payload = "|".join(
            [lead.name, lead.email, lead.service, lead.details, str(lead.marketing_consent), created]
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cur = self.db.execute(
            """
            INSERT INTO leads
            (name,email,service,details,marketing_consent,created_at,content_hash,status)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                lead.name,
                lead.email,
                lead.service,
                lead.details,
                int(lead.marketing_consent),
                created,
                digest,
                "NEW",
            ),
        )
        self.db.commit()
        return LeadOut(id=cur.lastrowid, **lead.model_dump(), created_at=created,
                       content_hash=digest, status="NEW")

    def get(self, lead_id: int) -> LeadOut:
        row = self.db.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        if row is None:
            raise KeyError(lead_id)
        return LeadOut(
            id=row["id"], name=row["name"], email=row["email"], service=row["service"],
            details=row["details"], marketing_consent=bool(row["marketing_consent"]),
            created_at=row["created_at"], content_hash=row["content_hash"],
            status=row["status"],
        )


def create_app(store: LeadStore | None = None) -> FastAPI:
    app = FastAPI(title="Electronic Brain Customer Portal API", version="1.0")
    lead_store = store or LeadStore()
    case_store = CustomerCaseStore()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "customer-portal"}

    @app.post("/v1/leads", response_model=LeadOut, status_code=201)
    def create_lead(lead: LeadIn) -> LeadOut:
        created = lead_store.create(lead)
        case_id = case_store.create_case(created.id)
        return created.model_copy(update={"status": f"NEW|CASE:{case_id}"})

    @app.get("/v1/leads/{lead_id}", response_model=LeadOut)
    def get_lead(lead_id: int) -> LeadOut:
        try:
            return lead_store.get(lead_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="lead_not_found")

    return app


app = create_app()
