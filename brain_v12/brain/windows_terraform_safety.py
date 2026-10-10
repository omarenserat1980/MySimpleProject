from __future__ import annotations

import re
from pathlib import Path


FORBIDDEN_TRACKED_NAMES = {
    "terraform.tfstate",
    "terraform.tfstate.backup",
    "brain.tfplan",
    "brain-windows.tfplan",
}

FORBIDDEN_OPEN_NETWORKS = {"0.0.0.0/0", "::/0"}
OPEN_NETWORK_ASSIGNMENT_PATTERNS = (
    re.compile(r"""(?im)^\s*(?:source_address_prefix(?:es)?|source_cidr|cidr_blocks|address_prefixes)\s*=.*["'](?:0\.0\.0\.0/0|::/0)["']"""),
)
SENSITIVE_TFVARS_PATTERNS = ("*.tfvars", "*.tfvars.json", "*.auto.tfvars", "*.auto.tfvars.json")
INLINE_SECRET_PATTERNS = (
    re.compile(r"""^\s*client_secret\s*=\s*["']"""),
    re.compile(r"""^\s*admin_password\s*=\s*["']"""),
)


def inspect_windows_terraform_root(
    root: str | Path,
    *,
    allow_runtime_plan: bool = False,
) -> dict[str, object]:
    root = Path(root)
    violations: list[str] = []

    forbidden_names = set(FORBIDDEN_TRACKED_NAMES)
    if allow_runtime_plan:
        forbidden_names.discard("brain.tfplan")

    for name in forbidden_names:
        if (root / name).exists():
            violations.append(f"FORBIDDEN_STATE_OR_PLAN_FILE:{name}")

    for path in root.rglob("*"):
        if path.is_file() and any(path.match(pattern) for pattern in SENSITIVE_TFVARS_PATTERNS):
            violations.append(f"SENSITIVE_TFVARS_FILE:{path.name}")
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(pattern.search(text) for pattern in OPEN_NETWORK_ASSIGNMENT_PATTERNS):
                violations.append(f"OPEN_NETWORK_RULE:{path.name}")
            if any(pattern.search(text) for pattern in INLINE_SECRET_PATTERNS):
                for pattern in INLINE_SECRET_PATTERNS:
                    if pattern.search(text):
                        label = "CLIENT_SECRET" if "client_secret" in pattern.pattern else "ADMIN_PASSWORD"
                        violations.append(f"INLINE_{label}:{path.name}")
                        break

    return {
        "safe": not violations,
        "violations": sorted(set(violations)),
        "root": str(root),
        "runtime_plan_allowed": allow_runtime_plan,
    }
