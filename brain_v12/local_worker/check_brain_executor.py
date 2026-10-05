#!/usr/bin/env python3
"""Fail-closed readiness probe for the Brain-owned executor."""

from __future__ import annotations

import json
import sys

from platform_foundation.brain_execution_authority import BrainExecutionAuthority


def main() -> int:
    result = BrainExecutionAuthority().readiness("ci")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
