"""SQLite persistence for Electronic Brain marketing campaigns.

The storage layer is deliberately separate from publishing adapters. It provides
durable campaign state and audit events without requiring a paid service.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .marketing_engine import Campaign, CampaignState


class CampaignStore:
    """Durable SQLite store for campaigns and their audit history."""

    def __init__(self, path: str | Path = "data/marketing.db") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                objective TEXT NOT NULL,
                audience TEXT NOT NULL,
                channels_json TEXT NOT NULL,
                content TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                approvals_json TEXT NOT NULL,
                events_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL
            )
            """
        )
        self._db.commit()

    def save(self, campaign: Campaign) -> None:
        self._db.execute(
            """
            INSERT INTO campaigns
            (id,name,objective,audience,channels_json,content,state,created_at,
             approvals_json,events_json,metrics_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name,
              objective=excluded.objective,
              audience=excluded.audience,
              channels_json=excluded.channels_json,
              content=excluded.content,
              state=excluded.state,
              created_at=excluded.created_at,
              approvals_json=excluded.approvals_json,
              events_json=excluded.events_json,
              metrics_json=excluded.metrics_json
            """,
            (
                campaign.id,
                campaign.name,
                campaign.objective,
                campaign.audience,
                json.dumps(campaign.channels),
                campaign.content,
                campaign.state.value,
                campaign.created_at,
                json.dumps(campaign.approvals),
                json.dumps(campaign.events),
                json.dumps(campaign.metrics),
            ),
        )
        self._db.commit()

    def get(self, campaign_id: str) -> Campaign:
        row = self._db.execute(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
        if row is None:
            raise KeyError(campaign_id)
        return Campaign(
            name=row["name"],
            objective=row["objective"],
            audience=row["audience"],
            channels=json.loads(row["channels_json"]),
            content=row["content"],
            id=row["id"],
            state=CampaignState(row["state"]),
            created_at=row["created_at"],
            approvals=json.loads(row["approvals_json"]),
            events=json.loads(row["events_json"]),
            metrics=json.loads(row["metrics_json"]),
        )

    def list(self, state: CampaignState | None = None) -> list[Campaign]:
        if state is None:
            rows = self._db.execute(
                "SELECT id FROM campaigns ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT id FROM campaigns WHERE state = ? ORDER BY created_at DESC",
                (state.value,),
            ).fetchall()
        return [self.get(row["id"]) for row in rows]

    def close(self) -> None:
        self._db.close()


def campaign_dict(campaign: Campaign) -> dict[str, Any]:
    """Return a JSON-safe campaign snapshot for APIs/UI."""
    return {
        "id": campaign.id,
        "name": campaign.name,
        "objective": campaign.objective,
        "audience": campaign.audience,
        "channels": campaign.channels,
        "content": campaign.content,
        "state": campaign.state.value,
        "created_at": campaign.created_at,
        "approvals": campaign.approvals,
        "events": campaign.events,
        "metrics": campaign.metrics,
    }
