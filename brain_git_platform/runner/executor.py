from __future__ import annotations
import subprocess
from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class StepResult:
    command:str
    returncode:int
    stdout:str
    stderr:str

class BrainRunnerExecutor:
    """Conservative native runner: only executes declared local commands."""
    def __init__(self, workspace: Path):
        self.workspace=workspace.resolve()
        self.workspace.mkdir(parents=True,exist_ok=True)

    def run_step(self, command:list[str], timeout:int=900)->StepResult:
        if not command or any(not isinstance(x,str) or not x for x in command):
            raise ValueError("command must be a non-empty string list")
        p=subprocess.run(command,cwd=self.workspace,text=True,capture_output=True,timeout=timeout)
        return StepResult(" ".join(command),p.returncode,p.stdout,p.stderr)

    def run_python_tests(self)->StepResult:
        return self.run_step(["python","-m","unittest","discover","-s","brain_git_platform","-p","test_*.py"])
