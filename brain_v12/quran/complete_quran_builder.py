#!/usr/bin/env python3
"""Process the complete Quran verse-by-verse for BRAIN.

The pipeline registers the exact source text and builds a deterministic
engineering record for every ayah. It deliberately does NOT auto-generate
tafsir or claim that a verse means a scientific/programming rule. Semantic
rules require an attributed tafsir/knowledge source and human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import urllib.parse
import urllib.request
from typing import Any, Iterable

EXPECTED_AYAHS = 6236
EXPECTED_SURAHS = 114
DEFAULT_SOURCE = (
    "https://tanzil.net/pub/download/index.php?"
    "quranType=uthmani&outType=txt-2&agree=true&marks=true"
    "&sajdah=true&rub=true&stanween=true"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_source(url: str) -> str:
    """Fetch the Tanzil export using its documented POST form contract."""
    params = {
        "quranType": "uthmani",
        "outType": "txt-2",
        "agree": "true",
        "marks": "true",
        "sajdah": "true",
        "rub": "true",
        "stanween": "true",
    }
    target = url.split("?", 1)[0]
    request = urllib.request.Request(
        target,
        data=urllib.parse.urlencode(params).encode("ascii"),
        headers={
            "User-Agent": "BRAIN-Quran-Pipeline/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/plain,*/*",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8-sig")
    if not text.strip():
        raise RuntimeError("QURAN_SOURCE_EMPTY")
    return text


def parse_tanzil_lines(text: str) -> list[tuple[str, str]]:
    verses: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            continue
        key, verse = line.split("|", 1)
        if ":" not in key or not verse.strip():
            continue
        verses.append((key.strip(), verse.strip()))
    return verses


def build_record(index: int, key: str, verse: str) -> dict[str, Any]:
    surah, ayah = (int(x) for x in key.split(":", 1))
    return {
        "global_ayah": index,
        "verse_key": key,
        "surah": surah,
        "ayah": ayah,
        "text_sha256": sha256_text(verse),
        "pipeline": {
            "text_registered": True,
            "source_verified": True,
            "semantic_interpretation": "NOT_AUTO_GENERATED",
            "tafsir_required_for_meaning_rules": True,
            "audit_required": True,
        },
    }


def process(verses: Iterable[tuple[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = [build_record(i, key, verse) for i, (key, verse) in enumerate(verses, 1)]
    keys = [r["verse_key"] for r in records]
    surahs = {r["surah"] for r in records}
    if len(records) != EXPECTED_AYAHS:
        raise RuntimeError(f"QURAN_AYAH_COUNT={len(records)} expected={EXPECTED_AYAHS}")
    if len(surahs) != EXPECTED_SURAHS:
        raise RuntimeError(f"QURAN_SURAH_COUNT={len(surahs)} expected={EXPECTED_SURAHS}")
    if len(set(keys)) != EXPECTED_AYAHS:
        raise RuntimeError("QURAN_DUPLICATE_VERSE_KEYS=FAIL")
    if keys[0] != "1:1" or keys[-1] != "114:6":
        raise RuntimeError(f"QURAN_RANGE={keys[0]}..{keys[-1]} unexpected")
    manifest = {
        "status": "REGISTERED",
        "ayah_count": len(records),
        "surah_count": len(surahs),
        "first_ayah": keys[0],
        "last_ayah": keys[-1],
        "record_count": len(records),
        "semantic_policy": "No automatic tafsir or scientific claims.",
    }
    return records, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", default=DEFAULT_SOURCE)
    parser.add_argument("--source-file", type=pathlib.Path)
    parser.add_argument("--out-dir", type=pathlib.Path, default=pathlib.Path(".brain/quran"))
    args = parser.parse_args()

    text = args.source_file.read_text(encoding="utf-8-sig") if args.source_file else fetch_source(args.source_url)
    verses = parse_tanzil_lines(text)
    records, manifest = process(verses)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    (args.out_dir / "verse_registry.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"QURAN_AYAH_COUNT={manifest['ayah_count']}")
    print(f"QURAN_SURAH_COUNT={manifest['surah_count']}")
    print("QURAN_VERSE_BY_VERSE_BUILD=PASS")
    print("QURAN_SEMANTIC_POLICY=TAFSIR_REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
