#!/usr/bin/env python3
"""Fail-closed live autonomy gate for Brain."""
from __future__ import annotations

import json
import sys

from tools.brain_autonomy_status import evaluate


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["AUTONOMOUS_WITHIN_AUTHORITY"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
