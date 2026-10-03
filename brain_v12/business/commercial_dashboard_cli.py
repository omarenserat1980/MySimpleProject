"""CLI report for the Brain commercial operations dashboard.

The command is read-only and prints evidence-backed commercial state. It does
not contact prospects, charge customers, or move funds.
"""
from __future__ import annotations

import json

from brain_v12.business.commercial_operations_dashboard import (
    build_commercial_operations_dashboard,
)
from brain_v12.business.initial_monetization_catalog import INITIAL_MONETIZATION_CATALOG


def build_initial_commercial_dashboard() -> dict:
    dashboard = build_commercial_operations_dashboard(
        INITIAL_MONETIZATION_CATALOG,
        [],
    )
    return dashboard.to_record()


def main() -> int:
    print(json.dumps(build_initial_commercial_dashboard(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
