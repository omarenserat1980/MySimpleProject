#!/usr/bin/env python3
"""Safely list the largest files beneath a directory.

Read-only by design: this tool never deletes, moves, or modifies scanned files.
It skips symlinks (including symlinked directories) and reports filesystem errors.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any


def candidate_download_dirs() -> list[Path]:
    """Return common Downloads locations, ordered by preference."""
    home = Path.home()
    candidates = [
        home / "Downloads",
        home / "storage" / "downloads",  # common Termux shared-storage path
        Path("/storage/emulated/0/Download"),
        Path("/sdcard/Download"),
    ]
    seen: set[str] = set()
    result: list[Path] = []
    for candidate in candidates:
        key = os.path.abspath(os.fspath(candidate))
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return result


def resolve_root(value: str | None) -> Path:
    """Resolve an explicit root or find the first existing Downloads folder."""
    if value:
        root = Path(value).expanduser()
        if not root.exists():
            raise FileNotFoundError(f"Directory does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")
        return root.resolve()

    for candidate in candidate_download_dirs():
        try:
            if candidate.is_dir():
                return candidate.resolve()
        except OSError:
            continue
    options = ", ".join(str(p) for p in candidate_download_dirs())
    raise FileNotFoundError(
        "Could not find a Downloads directory. Pass --root PATH. "
        f"Checked: {options}"
    )


def scan_largest_files(root: Path, limit: int = 5, include_hidden: bool = False) -> dict[str, Any]:
    """Scan regular files under root without following symlinks; return largest first."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    files: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    directories: list[Path] = [root]
    scanned_files = 0

    while directories:
        current = directories.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if not include_hidden and entry.name.startswith("."):
                        continue
                    path = Path(entry.path)
                    try:
                        # Do not follow symlinks; avoid escaping the chosen root.
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            directories.append(path)
                        elif entry.is_file(follow_symlinks=False):
                            stat = entry.stat(follow_symlinks=False)
                            scanned_files += 1
                            files.append({
                                "path": str(path),
                                "name": entry.name,
                                "size_bytes": stat.st_size,
                                "modified_time": stat.st_mtime,
                            })
                    except OSError as exc:
                        errors.append({"path": str(path), "error": str(exc)})
        except OSError as exc:
            errors.append({"path": str(current), "error": str(exc)})

    files.sort(key=lambda item: (-item["size_bytes"], item["path"].casefold(), item["path"]))
    return {
        "root": str(root),
        "limit": limit,
        "scanned_files": scanned_files,
        "errors": sorted(errors, key=lambda item: item["path"]),
        "files": files[:limit],
    }


def format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{size_bytes} B"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Find the largest files in Downloads (or another directory), read-only."
    )
    parser.add_argument("--root", help="directory to scan; defaults to a detected Downloads folder")
    parser.add_argument("--limit", type=int, default=5, help="number of largest files to show (default: 5)")
    parser.add_argument("--include-hidden", action="store_true", help="include files and directories whose names start with a dot")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable JSON report")
    parser.add_argument("--csv", action="store_true", help="emit CSV rows to stdout")
    args = parser.parse_args(argv)

    if args.json and args.csv:
        parser.error("--json and --csv cannot be used together")
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    try:
        root = resolve_root(args.root)
        report = scan_largest_files(root, args.limit, args.include_hidden)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.csv:
        writer = csv.DictWriter(sys.stdout, fieldnames=("name", "size_bytes", "path", "modified_time"))
        writer.writeheader()
        writer.writerows(report["files"])
    else:
        print(f"Root: {report['root']}")
        print(f"Regular files scanned: {report['scanned_files']}")
        if not report["files"]:
            print("No matching files found.")
        for rank, item in enumerate(report["files"], 1):
            print(f"{rank}. {item['name']} — {format_size(item['size_bytes'])}")
            print(f"   {item['path']}")
        if report["errors"]:
            print(f"\nWarnings: {len(report['errors'])} path(s) could not be scanned.")
            for error in report["errors"][:10]:
                print(f"  {error['path']}: {error['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
