"""Read-only API for Electronic Brain's curated open-source tool catalog."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["open-source-tools"])
CATALOG_PATH = Path(__file__).resolve().parents[1] / "open_source_tools" / "catalog.json"


def read_catalog() -> dict[str, Any]:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported open-source catalog schema")
    return data


@router.get("/api/open-source-tools")
def open_source_tools(category: str | None = Query(default=None)) -> dict[str, Any]:
    """List catalog entries. This endpoint never installs or executes software."""
    try:
        catalog = read_catalog()
    except (OSError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="OPEN_SOURCE_CATALOG_UNAVAILABLE")
    categories = catalog.get("categories", [])
    valid = {item.get("id") for item in categories}
    if category is not None and category not in valid:
        raise HTTPException(status_code=400, detail="UNKNOWN_TOOL_CATEGORY")
    tools = []
    for item in categories:
        if category and item.get("id") != category:
            continue
        for tool in item.get("tools", []):
            tools.append({"category": item["id"], **tool})
    return {
        "ok": True,
        "mode": "catalog_only",
        "execution_enabled": False,
        "count": len(tools),
        "categories": [{"id": x["id"], "title": x["title"]} for x in categories],
        "tools": tools,
    }


@router.get("/api/open-source-tools/{tool_id}")
def open_source_tool_detail(tool_id: str) -> dict[str, Any]:
    """Return one tool's catalog metadata by stable id."""
    try:
        catalog = read_catalog()
    except (OSError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="OPEN_SOURCE_CATALOG_UNAVAILABLE")
    for category in catalog.get("categories", []):
        for tool in category.get("tools", []):
            if tool.get("id") == tool_id:
                return {"ok": True, "mode": "catalog_only", "execution_enabled": False,
                        "category": category["id"], "tool": tool}
    raise HTTPException(status_code=404, detail="OPEN_SOURCE_TOOL_NOT_FOUND")
