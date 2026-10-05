from __future__ import annotations

"""Static safety checks for the Brain Windows Cloud Terraform root."""

from pathlib import Path


FORBIDDEN_TRACKED_NAMES = {
    "terraform.tfstate",
    "terraform.tfstate.backup",
    "brain.tfplan",
}

FORBIDDEN_OPEN_NETWORKS = {"0.0.0.0/0", "::/0"}
SENSITIVE_TFVARS_PATTERNS = ("*.tfvars", "*.tfvars.json", "*.auto.tfvars", "*.auto.tfvars.json")


def inspect_windows_terraform_root(root: str | Path) -> dict[str, object]:
    root = Path(root)
    violations: list[str] = []

    for name in FORBIDDEN_TRACKED_NAMES:
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
            if "0.0.0.0/0" in text or "::/0" in text:
                violations.append(f"OPEN_NETWORK_RULE:{path.name}")
            if "client_secret =" in text or "client_secret=" in text:
                violations.append(f"INLINE_CLIENT_SECRET:{path.name}")
            if "admin_password =" in text or "admin_password=" in text:
                violations.append(f"INLINE_ADMIN_PASSWORD:{path.name}")

    return {
        "safe": not violations,
        "violations": sorted(set(violations)),
        "root": str(root),
    }
