# Brain Runner

A Brain runner is an isolated execution worker registered with the internal scheduler.

Required capabilities:

- checkout/fetch from Brain Git storage
- execute workflow steps
- stream logs
- upload artifacts
- report exit status
- heartbeat
- receive short-lived scoped credentials

Runners must not require a GitHub Actions runner registration.
