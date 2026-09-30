#!/usr/bin/env python3
"""Dependency-free tests for the Brain self-healing core."""
from brain_v12.self_healing.supervisor import diagnose


def main() -> int:
    checks = [
        ("missing-token", diagnose("", "GITHUB_TOKEN_REQUIRED", 2)),
        ("syntax", diagnose("", "SyntaxError: invalid syntax", 1)),
        ("network", diagnose("", "Connection reset by peer", 1)),
        ("dependency", diagnose("", "ModuleNotFoundError: No module named x", 1)),
    ]
    failed = [name for name, result in checks if name not in result]
    if failed:
        print("SELF_TEST_FAILED", ",".join(failed))
        return 1
    print("SELF_TEST=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
