#!/usr/bin/env python3
"""Ingest Quranic Arabic Corpus-style linguistic annotations into BRAIN.

Input is a TSV/CSV-like file with one token per line. Required fields:
verse_key, token_index, surface, root, lemma, pos, features, relation, head.

The importer validates references and keeps linguistic annotation separate from
tafsir and scientific claims. It does not infer meanings from morphology.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


REQUIRED = {
    "verse_key",
    "token_index",
    "surface",
    "root",
    "lemma",
    "pos",
    "features",
    "relation",
    "head",
}


def read_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
        reader = csv.DictReader(fh, dialect=dialect)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError("missing columns: " + ",".join(sorted(missing)))
        yield from reader


def build_graph(rows):
    verses = defaultdict(list)
    for row in rows:
        key = row["verse_key"].strip()
        if ":" not in key:
            raise ValueError("invalid verse_key: " + key)
        token = {
            "index": int(row["token_index"]),
            "surface": row["surface"],
            "root": row["root"],
            "lemma": row["lemma"],
            "pos": row["pos"],
            "features": row["features"],
            "relation": row["relation"],
            "head": int(row["head"]),
        }
        verses[key].append(token)

    for key, tokens in verses.items():
        indexes = [t["index"] for t in tokens]
        if indexes != sorted(indexes) or len(indexes) != len(set(indexes)):
            raise ValueError("token order/duplicates in " + key)
        heads = {t["head"] for t in tokens}
        if any(h < 0 or h > len(tokens) for h in heads):
            raise ValueError("invalid dependency head in " + key)

    return {
        "verses": dict(verses),
        "policy": {
            "linguistic_annotation_only": True,
            "tafsir_generated": False,
            "scientific_claims_generated": False,
            "source_attribution_required": True,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    graph = build_graph(read_rows(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("QURAN_LINGUISTIC_INGEST=PASS")
    print("VERSES_WITH_LINGUISTIC_DATA=" + str(len(graph["verses"])))


if __name__ == "__main__":
    main()
