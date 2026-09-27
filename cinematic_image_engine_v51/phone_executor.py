from __future__ import annotations
import json, os, shlex, shutil, subprocess
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ExecutorResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0

class PhoneExecutor:
    """Terminal-agnostic Android command executor.

    Modes:
      - direct: execute a local executable with subprocess
      - bridge: execute EB_EXECUTOR_COMMAND as a command template
    """
    def __init__(self, config=None):
        self.config = config or {}
        self.mode = os.environ.get("EB_EXECUTOR_MODE", self.config.get("executor", {}).get("mode", "auto"))
        self.command = os.environ.get("EB_EXECUTOR_COMMAND", self.config.get("executor", {}).get("command", ""))
        self.timeout = int(os.environ.get("EB_EXECUTOR_TIMEOUT", self.config.get("executor", {}).get("timeout", 1800)))

    def discover(self):
        out = []
        termux = Path("/data/data/com.termux/files/usr").exists()
        if termux:
            out.append({"type":"direct","name":"termux","available":True})
        if self.command:
            exe = shlex.split(self.command)[0]
            out.append({"type":"bridge","name":"configured","command":self.command,
                        "available": bool(shutil.which(exe) or Path(exe).exists())})
        return out

    def run(self, argv, *, cwd=None, env=None):
        if self.mode == "bridge" or (self.mode == "auto" and self.command):
            payload = json.dumps({"argv":[str(x) for x in argv], "cwd":str(cwd or Path.cwd())},
                                 ensure_ascii=False)
            command = self.command.format(payload=shlex.quote(payload),
                                          argv=" ".join(shlex.quote(str(x)) for x in argv))
            p = subprocess.run(command, shell=True, cwd=cwd, env=env, text=True,
                               capture_output=True, timeout=self.timeout)
        else:
            p = subprocess.run([str(x) for x in argv], cwd=cwd, env=env, text=True,
                               capture_output=True, timeout=self.timeout)
        return ExecutorResult(p.returncode == 0, p.stdout, p.stderr, p.returncode)

    def image_command(self, executable, prompt, output, options=None):
        options = options or {}
        return self.run([executable, "--prompt", prompt, "--output", str(output), *options.get("args", [])])

def executor_probe():
    e = PhoneExecutor()
    return {"mode":e.mode, "bridge_configured":bool(e.command), "executors":e.discover()}
