#!/usr/bin/env python3
"""Safely compute a cloud executor enrollment SHA-256 without printing its token.

Run locally in a trusted terminal. The token is read with input echo disabled;
only the executor ID and digest are printed. Never pass the token as a CLI argument.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executor-id", required=True, help="Exact stable executor ID configured on the runner")
    args = parser.parse_args()
    token = getpass.getpass("Paste the existing executor token (input hidden): ")
    if not token:
        print("ERROR: empty token; no digest generated.", file=sys.stderr)
        return 2
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    # Output only the non-secret digest mapping; never echo token or raw request data.
    print(json.dumps({args.executor_id: digest}, indent=2))
    print("Merge this entry into BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON; do not replace other executor entries.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
