#!/usr/bin/env python3
"""Adapter for a reviewed Quranic Arabic Corpus export.

The adapter normalizes common corpus columns into BRAIN's linguistic schema.
It does not download third-party data, infer tafsir, or create scientific
claims. Source provenance must be supplied separately.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ALIASES = {
    "verse_key": ["verse_key", "ayah", "verse", "location"],
    "token_index": ["token_index", "word", "token"],
    "surface": ["surface", "form", "word_text"],
    "root": ["root"],
    "lemma": ["lemma", "lexeme"],
    "pos": ["pos", "part_of_speech", "tag"],
    "features": ["features", "morphology", "morph_features"],
    "relation": ["relation", "dependency", "syntactic_relation"],
    "head": ["head", "dependency_head", "parent"],
}


def pick(row, names, required=True):
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    if required:
        raise ValueError("missing required field: " + "/".join(names))
    return ""


def normalize(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(8192)
        fh.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,;")
        reader = csv.DictReader(fh, dialect=dialect)
        for row in reader:
            yield {
                "verse_key": pick(row, ALIASES["verse_key"]),
                "token_index": int(pick(row, ALIASES["token_index"])),
                "surface": pick(row, ALIASES["surface"]),
                "root": pick(row, ALIASES["root"], required=False),
                "lemma": pick(row, ALIASES["lemma"], required=False),
                "pos": pick(row, ALIASES["pos"], required=False),
                "features": pick(row, ALIASES["features"], required=False),
                "relation": pick(row, ALIASES["relation"], required=False),
                "head": int(pick(row, ALIASES["head"], required=False) or 0),
            }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    rows = list(normalize(args.input))
    if not rows:
        raise RuntimeError("CORPUS_EXPORT_EMPTY")

    verses = sorted({r["verse_key"] for r in rows})
    if any(":" not in v for v in verses):
        raise RuntimeError("INVALID_VERSE_KEY")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("QURAN_CORPUS_ADAPTER=PASS")
    print("TOKENS=" + str(len(rows)))
    print("VERSES=" + str(len(verses)))


if __name__ == "__main__":
    main()
