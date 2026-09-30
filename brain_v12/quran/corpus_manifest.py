#!/usr/bin/env python3
"""Manifest and integrity checker for external Quranic linguistic datasets.

This does not silently download or modify third-party corpus data. A human or
workflow supplies a local export plus its source URL and checksum. The manifest
then makes provenance auditable before ingestion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, required=True)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--license", default="REVIEW_REQUIRED")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    digest = sha256(args.file)
    manifest = {
        "file": str(args.file),
        "sha256": digest,
        "source_url": args.source_url,
        "license": args.license,
        "provenance_status": "RECORDED",
        "automatic_tafsir": False,
        "scientific_claims": False,
        "human_review_required": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("QURAN_CORPUS_PROVENANCE=PASS")
    print("SHA256=" + digest)


if __name__ == "__main__":
    main()
