"""Safe catalog CLI for Electronic Brain's open-source tool integrations.

This module is intentionally non-executing: it never installs packages, downloads
repositories, launches processes, flashes hardware, or provisions virtual machines.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_CATALOG = (
    Path(__file__).resolve().parents[1] / "open_source_tools" / "catalog.json"
)


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported catalog schema_version")
    if not isinstance(data.get("categories"), list):
        raise ValueError("Catalog categories must be a list")
    seen: set[str] = set()
    for category in data["categories"]:
        for tool in category.get("tools", []):
            tool_id = tool.get("id")
            if not tool_id or tool_id in seen:
                raise ValueError(f"Missing or duplicate tool id: {tool_id!r}")
            seen.add(tool_id)
            if not str(tool.get("repo", "")).startswith(("https://github.com/", "https://gitlab.com/", "https://git.savannah.gnu.org/")):
                raise ValueError(f"Unexpected upstream URL for {tool_id}")
            if tool.get("integration") == "hardware_adapter_gated" and not tool.get("priority"):
                raise ValueError(f"Hardware tool {tool_id} must have a priority")
    return data


def list_tools(catalog: dict[str, Any], category_id: str | None = None) -> list[dict[str, str]]:
    result = []
    for category in catalog["categories"]:
        if category_id and category["id"] != category_id:
            continue
        for tool in category.get("tools", []):
            result.append({
                "category": category["id"],
                "id": tool["id"],
                "name": tool["name"],
                "repo": tool["repo"],
                "license": tool["license"],
                "integration": tool["integration"],
                "priority": tool["priority"],
            })
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Electronic Brain's open-source tool catalog (read-only).")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--category", choices=["boot_virtualization", "local_ai", "electronics"])
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        tools = list_tools(load_catalog(args.catalog), args.category)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(tools, indent=2))
    else:
        for item in tools:
            print(f'{item["id"]:16} {item["name"]} [{item["priority"]}]')
            print(f'  {item["repo"]}')
            print(f'  license={item["license"]}; integration={item["integration"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
