"""Brain Tool Foundry: safe, review-gated scaffolding for Brain-owned tools.

This module proposes and scaffolds tools; it does not execute generated code,
grant credentials, register tools for production, or bypass existing permission
gates. Generated tools remain inert until reviewed, tested, and explicitly
registered by the normal Brain tool registry.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
BASE_DIR = Path("brain_v12/generated_tools")
ALLOWED_TYPES = {"string", "integer", "number", "boolean", "object", "array"}
ALLOWED_PERMISSIONS = {
    "read", "write", "network", "secrets", "device", "publish",
    "financial", "destructive",
}
HIGH_RISK_PERMISSIONS = {
    "write", "network", "secrets", "device", "publish",
    "financial", "destructive",
}
SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")


class ProposalError(ValueError):
    """Raised when a tool proposal is incomplete or unsafe."""


def validate_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a declarative tool proposal."""
    if not isinstance(proposal, dict):
        raise ProposalError("proposal must be a JSON object")
    required = {"name", "purpose", "inputs", "outputs", "permissions"}
    missing = sorted(required - proposal.keys())
    extra = sorted(proposal.keys() - (required | {"owner", "risk_notes"}))
    if missing:
        raise ProposalError("missing fields: " + ", ".join(missing))
    if extra:
        raise ProposalError("unsupported fields: " + ", ".join(extra))

    name = proposal["name"]
    purpose = proposal["purpose"]
    if not isinstance(name, str) or not SLUG_RE.fullmatch(name):
        raise ProposalError("name must be a lowercase slug (a-z, 0-9, underscore)")
    if not isinstance(purpose, str) or not purpose.strip() or len(purpose) > 500:
        raise ProposalError("purpose must be a non-empty string of at most 500 chars")

    for field in ("inputs", "outputs"):
        value = proposal[field]
        if not isinstance(value, list):
            raise ProposalError(f"{field} must be a list")
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, dict) or set(item) - {"name", "type", "required", "description"}:
                raise ProposalError(f"each {field} entry must contain only name/type/required/description")
            key = item.get("name")
            if not isinstance(key, str) or not re.fullmatch(r"^[a-z][a-z0-9_]{0,63}$", key):
                raise ProposalError(f"invalid {field} field name")
            if key in seen:
                raise ProposalError(f"duplicate {field} field: {key}")
            seen.add(key)
            if item.get("type") not in ALLOWED_TYPES:
                raise ProposalError(f"unsupported type for {field}.{key}")
            if "required" in item and not isinstance(item["required"], bool):
                raise ProposalError(f"{field}.{key}.required must be boolean")
            if "description" in item and not isinstance(item["description"], str):
                raise ProposalError(f"{field}.{key}.description must be a string")

    permissions = proposal["permissions"]
    if not isinstance(permissions, list) or any(
        not isinstance(p, str) or p not in ALLOWED_PERMISSIONS for p in permissions
    ):
        raise ProposalError("permissions must be a list of approved permission labels")
    if len(set(permissions)) != len(permissions):
        raise ProposalError("permissions must not contain duplicates")

    owner = proposal.get("owner", "brain")
    if not isinstance(owner, str) or not owner.strip() or len(owner) > 100:
        raise ProposalError("owner must be a non-empty string of at most 100 chars")
    notes = proposal.get("risk_notes", "")
    if not isinstance(notes, str) or len(notes) > 2000:
        raise ProposalError("risk_notes must be a string of at most 2000 chars")

    normalized = {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "purpose": purpose.strip(),
        "owner": owner.strip(),
        "inputs": proposal["inputs"],
        "outputs": proposal["outputs"],
        "permissions": sorted(set(permissions)),
        "risk_notes": notes,
        "requires_human_review": bool(set(permissions) & HIGH_RISK_PERMISSIONS),
        "execution_enabled": False,
        "production_registration": "REVIEW_REQUIRED",
    }
    return normalized


def _within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def scaffold(proposal: dict[str, Any], root: str | Path = ".") -> Path:
    """Create inert proposal files in a fixed, repository-local directory."""
    normalized = validate_proposal(proposal)
    repo_root = Path(root).resolve()
    base = (repo_root / BASE_DIR).resolve()
    target = base / normalized["name"]
    if not _within(base, repo_root) or not _within(target, base):
        raise ProposalError("refusing to write outside the repository tool directory")
    if target.exists():
        raise ProposalError(f"target already exists: {target.relative_to(repo_root)}")
    target.mkdir(parents=True, exist_ok=False)

    manifest = target / "tool.json"
    implementation = target / "tool.py"
    readme = target / "README.md"
    try:
        manifest.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        implementation.write_text(
            '"""Generated Brain tool stub. Implement only after human review."""\n'
            'from __future__ import annotations\n\n'
            'TOOL_ENABLED = False\n\n'
            'def run(arguments: dict) -> dict:\n'
            '    """Inert stub: production execution is intentionally disabled."""\n'
            '    raise RuntimeError("TOOL_NOT_IMPLEMENTED_OR_APPROVED")\n',
            encoding="utf-8",
        )
        readme.write_text(
            f"# Brain tool proposal: {normalized['name']}\n\n"
            f"{normalized['purpose']}\n\n"
            "## Gate status\n"
            "- Proposal validated by the local Tool Foundry schema.\n"
            "- Generated implementation is inert and cannot run.\n"
            "- Human code review, tests, security review, and explicit registry "
            "registration are required before production use.\n"
            f"- Permissions requested: {', '.join(normalized['permissions']) or 'none'}\n"
            f"- Human review required: {normalized['requires_human_review']}\n",
            encoding="utf-8",
        )
    except Exception:
        # Do not leave a misleading partial scaffold behind.
        import shutil
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target


def _load(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProposalError(f"cannot load proposal JSON: {exc}") from exc
    return validate_proposal(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Brain Tool Foundry (safe, review-gated)")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_cmd = sub.add_parser("validate", help="validate a proposal JSON file")
    validate_cmd.add_argument("proposal")
    scaffold_cmd = sub.add_parser("scaffold", help="create inert files from a proposal")
    scaffold_cmd.add_argument("proposal")
    scaffold_cmd.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    try:
        proposal = _load(args.proposal)
        if args.command == "validate":
            print(json.dumps({"ok": True, "proposal": proposal}, indent=2, ensure_ascii=False))
        else:
            path = scaffold(proposal, args.root)
            print(json.dumps({
                "ok": True,
                "status": "SCAFFOLDED_INERT",
                "path": str(path),
                "execution_enabled": False,
                "requires_human_review": proposal["requires_human_review"],
            }, indent=2))
        return 0
    except ProposalError as exc:
        print(json.dumps({"ok": False, "status": "BLOCKED", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
