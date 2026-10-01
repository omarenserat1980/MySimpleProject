from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


@dataclass(frozen=True)
class RepairPlan:
    classification: str
    action: str
    confidence: str
    safe: bool
    path: str | None = None
    old: str | None = None
    new: str | None = None
    test_command: tuple[str, ...] = ()


class RepairEngine:
    """Bounded, allowlisted repair planner.

    It never invents arbitrary source edits. A source repair is allowed only
    when the error signature, target path, and exact old text all match a
    registered recipe.
    """

    ACTIONS = {\n        "EXECUTION_INFRA": "RERUN_FAILED_JOBS",\n        "MEDIA_OR_VM_PIPELINE": "RERUN_OR_FALLBACK_MEDIA",\n        "INPUT_OR_ARTIFACT": "REBUILD_ARTIFACT",\n        "DEPENDENCY_OR_IMPORT": "BLOCK_FOR_REVIEW",\n    }\n\n    RECIPES = (
        {
            "name": "verification_vm_load",
            "patterns": (r"not enough values to unpack", r"verification_suite\.py"),
            "path": "brain_v12/verification/verification_suite.py",
            "old": "vm = BrainVM()\nr = vm.run(max_steps=1000)",
            "new": "vm = BrainVM()\nvm.load(p)\nr = vm.run(max_steps=1000)",
            "test": ("python", "-m", "unittest", "brain_v12.verification.verification_suite", "-v"),
        },
    )

    def diagnose(self, log: str) -> str:
        text = str(log or "")
        if re.search(r"not enough values to unpack", text, re.I) and re.search(
            r"verification_suite\.py", text, re.I
        ):
            return "VERIFICATION_VM_NOT_LOADED"
        if re.search(r"ModuleNotFoundError|ImportError", text, re.I):
            return "DEPENDENCY_OR_IMPORT"
        if re.search(r"timeout|timed out|runner|queued|rate limit|502|503", text, re.I):
            return "EXECUTION_INFRA"
        if re.search(r"ffmpeg|ffprobe|concat|codec|mux|qemu|xorriso", text, re.I):
            return "MEDIA_OR_VM_PIPELINE"
        if re.search(r"No such file|cannot open|No input|artifact.*not found", text, re.I):
            return "INPUT_OR_ARTIFACT"
        return "UNKNOWN"

    def plan(self, log: str) -> RepairPlan:
        classification = self.diagnose(log)
        for recipe in self.RECIPES:
            if all(re.search(p, log or "", re.I) for p in recipe["patterns"]):
                return RepairPlan(
                    classification=classification,
                    action="APPLY_EXACT_PATCH",
                    confidence="HIGH",
                    safe=True,
                    path=recipe["path"],
                    old=recipe["old"],
                    new=recipe["new"],
                    test_command=tuple(recipe["test"]),
                )

        action = {
            "EXECUTION_INFRA": "RERUN_FAILED_JOBS",
            "MEDIA_OR_VM_PIPELINE": "FALLBACK_OR_RERUN",
            "INPUT_OR_ARTIFACT": "REBUILD_ARTIFACT",
            "DEPENDENCY_OR_IMPORT": "BLOCK_FOR_REVIEW",
        }.get(classification, "BLOCK_FOR_REVIEW")
        return RepairPlan(classification, action, "MEDIUM" if action != "BLOCK_FOR_REVIEW" else "LOW", False)

    def apply(self, root: str | Path, plan: RepairPlan) -> bool:
        if not plan.safe or plan.action != "APPLY_EXACT_PATCH" or not plan.path:
            return False
        target = Path(root) / plan.path
        if not target.is_file():
            return False
        text = target.read_text(encoding="utf-8")
        if plan.old not in text:
            return False
        if plan.new in text:
            return False
        target.write_text(text.replace(plan.old, plan.new, 1), encoding="utf-8")
        return True

    def validate(self, root: str | Path, plan: RepairPlan) -> bool:
        if not plan.test_command:
            return False
        proc = subprocess.run(
            plan.test_command,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        return proc.returncode == 0

    def repair(self, root: str | Path, log: str) -> tuple[RepairPlan, bool]:
        plan = self.plan(log)
        if not self.apply(root, plan):
            return plan, False
        try:
            ok = self.validate(root, plan)
        except (OSError, subprocess.SubprocessError):
            ok = False
        if not ok:
            # Roll back only the exact replacement we made.
            target = Path(root) / str(plan.path)
            text = target.read_text(encoding="utf-8")
            if plan.new and plan.old and plan.new in text:
                target.write_text(text.replace(plan.new, plan.old, 1), encoding="utf-8")
        return plan, ok


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("log_file")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    log = Path(args.log_file).read_text(encoding="utf-8", errors="replace")
    engine = RepairEngine()
    plan, ok = engine.repair(args.root, log)
    print(f"REPAIR_CLASSIFICATION={plan.classification}")
    print(f"REPAIR_ACTION={plan.action}")
    print(f"REPAIR_SAFE={plan.safe}")
    print(f"REPAIR_APPLIED_AND_VALIDATED={ok}")
    return 0 if (ok or plan.action != "APPLY_EXACT_PATCH") else 1


if __name__ == "__main__":
    raise SystemExit(main())
