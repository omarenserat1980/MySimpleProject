import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
env = os.environ.copy()
env.setdefault("AGENT_PORT", "9000")

print("Starting Electronic Brain Agent on http://127.0.0.1:9000")
subprocess.run([sys.executable, "agent.py"], cwd=ROOT, env=env, check=False)
