#!/usr/bin/env python3
"""Build the Quran Knowledge Graph from registered ayahs and reviewed annotations.

Input files:
- verse_registry.jsonl from complete_quran_builder.py
- optional reviewed annotations JSONL with:
  verse_key, concept_id, concept_label, source, relation, evidence, confidence

The builder never infers semantic edges from a root/lemma alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from brain_v12.quran.quran_knowledge_graph import QuranKnowledgeGraph


def load_registry(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def build(registry: Path, annotations: Path | None):
    graph = QuranKnowledgeGraph()

    for row in load_registry(registry):
        graph.add_ayah(row["verse_key"], row["text_sha256"])

    annotation_count = 0
    if annotations and annotations.exists():
        for row in load_registry(annotations):
            key = row["verse_key"]
            concept = row["concept_id"]
            graph.add_concept(
                concept,
                row["concept_label"],
                row["source"],
            )
            graph.link(
                key,
                row["relation"],
                concept,
                row["evidence"],
                row.get("confidence", "UNASSESSED"),
            )
            annotation_count += 1

    audit = graph.audit()
    if audit["uncited_edges"]:
        raise RuntimeError("uncited semantic edges detected")
    if len(graph.nodes) < 6236:
        raise RuntimeError("QURAN_GRAPH_AYAH_COVERAGE=FAIL")

    return graph, annotation_count, audit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, required=True)
    ap.add_argument("--annotations", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    graph, count, audit = build(args.registry, args.annotations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(graph.export(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("QURAN_GRAPH_BUILD=PASS")
    print("QURAN_GRAPH_NODES=" + str(audit["nodes"]))
    print("QURAN_GRAPH_EDGES=" + str(audit["edges"]))
    print("QURAN_REVIEWED_ANNOTATIONS=" + str(count))


if __name__ == "__main__":
    main()
