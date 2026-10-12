"""Safe project factory for Brain Habitat."""
from __future__ import annotations

from pathlib import Path
import re


NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,63}$")


class ProjectFactory:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _safe_project(self, name: str) -> Path:
        if not NAME_RE.fullmatch(name):
            raise ValueError("invalid project name")
        root = (self.workspace / name).resolve()
        if root.parent != self.workspace:
            raise ValueError("project escapes workspace")
        return root

    def create(self, name: str, kind: str = "python") -> dict:
        root = self._safe_project(name)
        if root.exists():
            raise FileExistsError(f"project already exists: {name}")
        if kind not in {"python", "android", "generic"}:
            raise ValueError("unsupported project kind")
        root.mkdir()
        (root / "README.md").write_text(f"# {name}\n\nCreated by Brain Habitat.\n", encoding="utf-8")
        if kind == "python":
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "__init__.py").write_text("", encoding="utf-8")
            (root / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
        elif kind == "android":
            (root / "app").mkdir()
            (root / "app" / "README.md").write_text("Android project workspace.\n", encoding="utf-8")
        else:
            (root / "src").mkdir()
            (root / "tests").mkdir()
        return {"ok": True, "project": name, "kind": kind, "path": str(root)}
