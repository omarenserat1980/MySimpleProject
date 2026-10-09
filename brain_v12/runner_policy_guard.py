from __future__ import annotations

from pathlib import Path
import json
import re


class RunnerPolicyViolation(RuntimeError):
    pass


class RunnerPolicyGuard:
    """Fail-closed guard for Brain-authoritative workflow execution."""

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        manifest = self.root / "brain_v12" / "execution_authority_manifest.json"
        self.manifest = json.loads(manifest.read_text(encoding="utf-8"))

    def assert_ready(self) -> dict[str, object]:
        result = self.validate()
        if not result["healthy"]:
            raise RunnerPolicyViolation(json.dumps(result, sort_keys=True))
        return result

    def validate(self) -> dict[str, object]:
        workflows = self.manifest["authoritative_workflows"]
        violations: list[dict[str, str]] = []
        for name in workflows:
            path = self.root / ".github" / "workflows" / name
            if not path.exists():
                violations.append({"workflow": name, "reason": "workflow_missing"})
                continue
            text = path.read_text(encoding="utf-8")
            if "ubuntu-latest" in text or "ubuntu-22.04" in text:
                violations.append({"workflow": name, "reason": "external_runner_reference"})
            if re.search(r"(?im)^\s*runs-on:\s*(?!\[self-hosted,\s*brain-runner\])", text):
                violations.append({"workflow": name, "reason": "brain_runner_label_missing"})
        return {
            "healthy": not violations,
            "status": "READY" if not violations else "BLOCKED",
            "violations": violations,
            "policy": self.manifest["policy"],
        }


__all__ = ["RunnerPolicyGuard", "RunnerPolicyViolation"]
