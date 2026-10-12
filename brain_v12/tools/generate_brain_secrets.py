from __future__ import annotations

"""Generate local Brain runtime secrets.

Secrets are printed once and are never written to the repository.
Use a secret manager, protected environment file, or platform secret store.
"""

import argparse
import secrets


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=2)
    args = p.parse_args()
    if args.count < 1 or args.count > 10:
        raise SystemExit("--count must be between 1 and 10")

    print("# Keep these values outside Git.")
    print("BRAIN_CONTROL_TOKEN=" + secrets.token_urlsafe(48))
    for i in range(1, args.count + 1):
        print(f"BRAIN_ENROLLMENT_TOKEN_{i}=" + secrets.token_urlsafe(32))
    print("# Rotate enrollment tokens after first successful registration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
