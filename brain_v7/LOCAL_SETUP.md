# Electronic Brain V7 — local setup

## 1) Install
python -m pip install -r requirements.txt

## 2) Create a secret token

Windows PowerShell:
$env:AGENT_TOKEN="ضع-رمزاً-سرياً-هنا"

Windows CMD:
set AGENT_TOKEN=ضع-رمزاً-سرياً-هنا

Linux/macOS/Termux:
export AGENT_TOKEN="ضع-رمزاً-سرياً-هنا"

## 3) Start the Agent
python run_agent.py

The Agent listens locally at:
http://127.0.0.1:9000

## 4) In a second terminal start the Brain

Windows PowerShell:
$env:AGENT_URL="http://127.0.0.1:9000"
$env:AGENT_TOKEN="ضع-نفس-الرمز-هنا"
python main.py

Linux/macOS/Termux:
export AGENT_URL="http://127.0.0.1:9000"
export AGENT_TOKEN="ضع-نفس-الرمز-هنا"
python main.py

The Brain API listens at:
http://127.0.0.1:8000

## 5) Test

Open:
http://127.0.0.1:8000/health

Then:
http://127.0.0.1:8000/api/agent/status

The Agent is intentionally local-only by default. System permission remains disabled unless explicitly enabled. Commands are restricted by the Agent allowlist and execution requests require explicit approval.

Never commit AGENT_TOKEN or LLM_API_KEY to GitHub.
