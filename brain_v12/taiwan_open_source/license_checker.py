"""Conservative license gate for external repositories."""
from __future__ import annotations
from pathlib import Path

APPROVED_HINTS = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}

def classify_license_text(text: str) -> str:
    upper = text.upper()
    if "MIT LICENSE" in upper or "PERMISSION IS HEREBY GRANTED" in upper:
        return "MIT"
    if "APACHE LICENSE" in upper and "VERSION 2.0" in upper:
        return "Apache-2.0"
    if "BSD 3-CLAUSE" in upper:
        return "BSD-3-Clause"
    if "BSD 2-CLAUSE" in upper:
        return "BSD-2-Clause"
    if not text.strip():
        return "UNKNOWN"
    return "OTHER_OR_UNVERIFIED"

def is_safe_for_adapter(license_name: str) -> bool:
    return license_name in APPROVED_HINTS

def inspect_license(repo_root: Path) -> dict:
    candidates = [repo_root/"LICENSE", repo_root/"LICENSE.txt", repo_root/"COPYING"]
    for path in candidates:
        if path.is_file():
            value = classify_license_text(path.read_text(encoding="utf-8", errors="replace"))
            return {"path": str(path), "license": value, "adapter_allowed": is_safe_for_adapter(value)}
    return {"path": None, "license": "UNKNOWN", "adapter_allowed": False}
