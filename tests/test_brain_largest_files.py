from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.brain_largest_files import format_size, scan_largest_files


def test_returns_largest_files_first_and_recurses(tmp_path: Path) -> None:
    (tmp_path / "small.txt").write_bytes(b"x" * 3)
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "large.bin").write_bytes(b"x" * 100)
    (nested / "medium.dat").write_bytes(b"x" * 20)

    report = scan_largest_files(tmp_path, limit=2)

    assert report["scanned_files"] == 3
    assert [item["name"] for item in report["files"]] == ["large.bin", "medium.dat"]
    assert report["files"][0]["size_bytes"] == 100
    assert report["errors"] == []


def test_hidden_files_are_excluded_by_default(tmp_path: Path) -> None:
    (tmp_path / ".secret").write_bytes(b"x" * 500)
    (tmp_path / "visible").write_bytes(b"x" * 10)

    report = scan_largest_files(tmp_path)

    assert [item["name"] for item in report["files"]] == ["visible"]


def test_hidden_files_can_be_included(tmp_path: Path) -> None:
    (tmp_path / ".secret").write_bytes(b"x" * 500)
    (tmp_path / "visible").write_bytes(b"x" * 10)

    report = scan_largest_files(tmp_path, include_hidden=True)

    assert [item["name"] for item in report["files"]] == [".secret", "visible"]


def test_limit_must_be_positive(tmp_path: Path) -> None:
    try:
        scan_largest_files(tmp_path, limit=0)
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError("expected ValueError for zero limit")


def test_ties_have_deterministic_path_order(tmp_path: Path) -> None:
    (tmp_path / "z.bin").write_bytes(b"same")
    (tmp_path / "a.bin").write_bytes(b"same")

    report = scan_largest_files(tmp_path, limit=2)

    assert [item["name"] for item in report["files"]] == ["a.bin", "z.bin"]


def test_cli_json_output(tmp_path: Path) -> None:
    (tmp_path / "sample.bin").write_bytes(b"x" * 7)
    script = Path(__file__).parents[1] / "tools" / "brain_largest_files.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)

    assert report["scanned_files"] == 1
    assert report["files"][0]["name"] == "sample.bin"
    assert report["files"][0]["size_bytes"] == 7


def test_format_size() -> None:
    assert format_size(0) == "0 B"
    assert format_size(1024) == "1.00 KB"
