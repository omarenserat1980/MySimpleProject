#!/usr/bin/env python3
"""Continuously audit public AI-video/free-tier signals for Brain.

This is a discovery/audit layer, not an auto-purchasing or auto-submission layer.
It records source reachability, content hashes, and public RSS headlines so Brain
can notice changes without assuming that a free tier is unlimited.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from brain_v12.brain.free_ai_capability_registry import snapshot

OUT = Path("brain6_artifacts")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Brain-Free-AI-Radar/1.0"


def fetch(url: str, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return int(getattr(r, "status", 200)), r.read().decode("utf-8", "ignore")


def rss_items(xml_text: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items = []
    for item in root.findall(".//item")[:20]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if title:
            items.append({"title": title, "link": link, "published": pub})
    return items


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    snap = snapshot()
    sources = []
    for tool in snap["tools"]:
        url = tool["official"]
        try:
            status, body = fetch(url)
            sources.append({
                "tool_id": tool["id"],
                "url": url,
                "status": status,
                "reachable": 200 <= status < 400,
                "sha256": hashlib.sha256(body.encode()).hexdigest(),
                "bytes": len(body.encode()),
            })
        except Exception as exc:
            sources.append({
                "tool_id": tool["id"], "url": url,
                "reachable": False, "error": str(exc)[:300],
            })

    queries = [
        "AI video generator free open source 2026",
        "free AI video generation API 2026",
        "open source video model release 2026",
    ]
    news = []
    for q in queries:
        rss = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"}
        )
        try:
            status, body = fetch(rss)
            if 200 <= status < 400:
                for item in rss_items(body):
                    item["query"] = q
                    news.append(item)
        except Exception as exc:
            news.append({"query": q, "error": str(exc)[:300]})

    # Keep the artifact compact and auditable.
    seen = set()
    deduped = []
    for item in news:
        key = (item.get("title"), item.get("link"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    report = {
        "generated_at": now,
        "classification": snap["policy"],
        "registry": snap["tools"],
        "official_source_audit": sources,
        "public_discovery": deduped[:50],
        "selection_rule": (
            "Brain may use zero-cost self-hosted models only when a compatible "
            "runner is available. Hosted free tiers remain quota-limited unless "
            "their current terms explicitly say otherwise."
        ),
    }
    (OUT / "free_ai_capabilities.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "ok": True,
        "tools": len(snap["tools"]),
        "reachable_sources": sum(1 for x in sources if x.get("reachable")),
        "discovery_items": len(deduped),
        "artifact": str(OUT / "free_ai_capabilities.json"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
