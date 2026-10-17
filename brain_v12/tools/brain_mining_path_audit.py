"""Read-only static audit of Brain mining paths and configuration references.

Never prints environment values, reads secret files, contacts a pool, starts a
miner, edits configuration, or changes production state.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

SOURCE_SUFFIXES = {".py", ".sh", ".yml", ".yaml", ".toml", ".ini"}
SKIP_PARTS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".brain",
    "brain6_artifacts", "evidence", "dist", "build",
}
SECRET_FILE_NAMES = {".env", ".brain_env", "secrets.env", "credentials.json"}
CONFIG_NAMES = (
    "BRAIINS_POOL_API_TOKEN",
    "BRAIINS_POOL_WORKER_ID",
    "BRAIN_MINING_WORKER_API_TOKEN",
    "BRAIN_MINING_API_URL",
    "BRAIN_MINING_WORKER_ID",
    "BRAIN_MINER_STATS_URL",
    "V12_BRAIN_URL",
)
MINING_FILE_RE = re.compile(
    r"(mining|braiin|stratum|bitcoin_worker|pool_evidence|secret_control|"
    r"mining_node|compute_runtime)",
    re.IGNORECASE,
)
ENV_RE = re.compile(r"\b(" + "|".join(map(re.escape, CONFIG_NAMES)) + r")\b")
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "api_route"}


def _git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True, capture_output=True, text=True, timeout=3,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _safe_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    # Prune excluded directories before descending; important on low-memory phones
    # and avoids walking Git object stores, virtualenvs, artifacts, and caches.
    for current, directories, names in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in SKIP_PARTS)
        current_path = Path(current)
        for name in names:
            path = current_path / name
            if path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            if path.name.lower() in SECRET_FILE_NAMES or path.name.lower().endswith(".secret"):
                continue
            files.append(path)
    return sorted(files)


def _literal_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _router_declarations(path: Path, relative: str, content: str) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]:
    """Return (method, full_path, file) declarations and (prefix, file) router declarations."""
    if path.suffix != ".py" or "/test" in f"/{relative.lower()}" or path.name.startswith("test_"):
        return [], []
    # Most files do not declare FastAPI routers; skip AST parsing for them.
    if "APIRouter" not in content or "router." not in content:
        return [], []
    try:
        tree = ast.parse(content, filename=relative)
    except SyntaxError:
        return [], []
    prefixes: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        func_name = value.func.id if isinstance(value.func, ast.Name) else (
            value.func.attr if isinstance(value.func, ast.Attribute) else ""
        )
        if func_name != "APIRouter":
            continue
        prefix = ""
        for kw in value.keywords:
            if kw.arg == "prefix":
                prefix = _literal_string(kw.value) or ""
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                prefixes[target.id] = prefix
    prefix_rows = [(prefix, relative) for prefix in prefixes.values()]
    route_rows: list[tuple[str, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr.lower()
            if method not in HTTP_METHODS or not isinstance(decorator.func.value, ast.Name):
                continue
            router_name = decorator.func.value.id
            if router_name not in prefixes or not decorator.args:
                continue
            route_path = _literal_string(decorator.args[0])
            if route_path is None:
                continue
            full_path = prefixes[router_name].rstrip("/") + "/" + route_path.lstrip("/")
            if not full_path:
                full_path = "/"
            if method == "api_route":
                methods = {"GET"}  # Conservative marker; dynamic methods are reviewed manually.
            else:
                methods = {method.upper()}
            route_rows.extend((http_method, full_path, relative) for http_method in methods)
    return route_rows, prefix_rows


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    source_files = _safe_source_files(root)
    config_references: dict[str, list[dict[str, Any]]] = {name: [] for name in CONFIG_NAMES}
    mining_files: list[str] = []
    simulator_files: list[str] = []
    pool_adapter_files: list[str] = []
    route_declarations: list[tuple[str, str, str]] = []
    prefix_declarations: list[tuple[str, str]] = []

    for path in source_files:
        rel = path.relative_to(root).as_posix()
        if MINING_FILE_RE.search(path.name):
            mining_files.append(rel)
        if re.search(r"(simulat|simulation)", path.name, re.IGNORECASE):
            simulator_files.append(rel)
        if "braiins" in path.name.lower() or "stratum_v1_transport" in path.name.lower():
            pool_adapter_files.append(rel)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(content.splitlines(), 1):
            for match in ENV_RE.finditer(line):
                config_references[match.group(1)].append({"file": rel, "line": line_no})
        routes, prefixes = _router_declarations(path, rel, content)
        route_declarations.extend(routes)
        prefix_declarations.extend(prefixes)

    prefix_map: dict[str, set[str]] = {}
    for prefix, path in prefix_declarations:
        prefix_map.setdefault(prefix, set()).add(path)
    shared_prefixes = {
        prefix: sorted(paths) for prefix, paths in sorted(prefix_map.items())
        if prefix and len(paths) > 1
    }
    route_map: dict[str, set[str]] = {}
    for method, route_path, path in route_declarations:
        route_map.setdefault(f"{method} {route_path}", set()).add(path)
    duplicate_routes = {
        route: sorted(paths) for route, paths in sorted(route_map.items())
        if len(paths) > 1
    }

    configured_names = [name for name, refs in config_references.items() if refs]
    branch = _git(root, "branch", "--show-current")
    commit = _git(root, "rev-parse", "--short", "HEAD")
    git_status = _git(root, "status", "--porcelain")
    dirty_count = len(git_status.splitlines()) if git_status else 0
    findings: list[str] = []
    if duplicate_routes:
        findings.append("DUPLICATE_STATIC_HTTP_METHOD_AND_PATH")
    if shared_prefixes:
        findings.append("SHARED_ROUTER_PREFIXES_REQUIRE_RUNTIME_REGISTRATION_REVIEW")
    if not simulator_files:
        findings.append("NO_STATIC_SIMULATOR_FILENAME_FOUND")
    if not pool_adapter_files:
        findings.append("NO_STATIC_BRAIINS_OR_STRATUM_TRANSPORT_FILENAME_FOUND")
    if not configured_names:
        findings.append("NO_RECOGNIZED_MINING_ENV_REFERENCES_FOUND")
    if dirty_count:
        findings.append("WORKTREE_HAS_LOCAL_CHANGES")
    findings.append("STATIC_AUDIT_CANNOT_PROVE_RUNTIME_ROUTE_REGISTRATION_OR_LIVE_MINING")

    return {
        "schema_version": 1,
        "audit": "brain-mining-path-audit",
        "mode": "READ_ONLY_STATIC",
        "repository_root": str(root),
        "git": {"branch": branch, "commit": commit, "dirty_file_count": dirty_count},
        "source_file_count": len(source_files),
        "mining_related_files": mining_files,
        "simulator_files": simulator_files,
        "pool_or_stratum_adapter_files": pool_adapter_files,
        "configuration_reference_locations": config_references,
        "shared_static_api_router_prefixes": shared_prefixes,
        "duplicate_static_api_routes": duplicate_routes,
        "findings": findings,
        "secrets_values_printed": False,
        "network_accessed": False,
        "miner_started": False,
        "files_modified": False,
        "production_settings_changed": False,
        "real_mining_verified": False,
        "accepted_shares_verified": False,
        "revenue_verified": False,
        "limitations": [
            "Static source inspection only; runtime imports and dynamic routes may differ.",
            "Environment variable presence and values are not read.",
            "A source filename or API reference does not prove that the component is active.",
            "Shared router prefixes are not automatically collisions; exact method/path duplicates are reported separately.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", action="store_true", help="Emit JSON (default format is JSON).")
    args = parser.parse_args()
    print(json.dumps(audit(args.root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
