# Electronic Brain V11 — Relay

## Architecture

```
External controller
       |
     HTTPS
       v
  Brain Relay
       ^
       | outbound HTTPS polling
       |
Android / Termux
       |
Electronic Brain
       |
     Agent
       |
     Termux
```

The Android device does **not** need an inbound public port.

## Run the relay

On a server with Python:

```bash
cd brain_v7
python -m pip install -r relay_requirements.txt
export RELAY_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export PORT=8080
python relay_server.py
```

For production, put the service behind HTTPS and keep `RELAY_TOKEN` secret.

## Configure Android / Termux

Inside `brain_v7`:

```bash
export RELAY_URL="https://YOUR-RELAY-DOMAIN"
export RELAY_TOKEN="THE-SAME-RANDOM-TOKEN"
export RELAY_ID="android-brain-01"
./start_brain.sh
```

The client polls `/v1/tasks/next`, executes the objective through the bounded autonomous task engine, then posts the result to `/v1/tasks/{id}/result`.

## Queue a task

From an authorized controller:

```bash
curl -X POST "https://YOUR-RELAY-DOMAIN/v1/tasks" \
  -H "Authorization: Bearer THE-SAME-RANDOM-TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"brain_id":"android-brain-01","objective":"inspect the project","timeout":30,"max_steps":8}'
```

Then query the task:

```bash
curl "https://YOUR-RELAY-DOMAIN/v1/tasks/TASK_ID" \
  -H "Authorization: Bearer THE-SAME-RANDOM-TOKEN"
```

## Important security boundary

The relay token is an authentication secret. Do not commit it to GitHub or paste it into chat.

The current Agent remains bounded by its registered actions and command policy. The relay does not grant unrestricted operating-system access.
