"""CLI for producing a governed design plan without executing the plan."""
from __future__ import annotations
import argparse
import json
from .plan import prepare_design_plan

def main() -> int:
    parser = argparse.ArgumentParser(description="Create an evidence-aware Electronic Brain design plan.")
    parser.add_argument("task", help="Plain-language task to route to specialist prompts")
    args = parser.parse_args()
    try:
        result = prepare_design_plan(args.task)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
