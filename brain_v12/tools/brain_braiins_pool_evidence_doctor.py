#!/usr/bin/env python3
"""Read-only Braiins Pool evidence doctor. Never starts or configures a miner."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from brain_v12.brain.braiins_pool_evidence_collector import collect_braiins_pool_evidence


def main() -> int:
    result = collect_braiins_pool_evidence()
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0 if result.get("status") == "POOL_ACTIVITY_OBSERVED" else 2


if __name__ == "__main__":
    sys.exit(main())
