# Brain Cloud Native

GitHub is the source-control/CI layer and Brain Cloud is the long-lived runtime.

- Render is not required.
- GitHub Actions builds/tests.
- Brain Cloud runs the API and workers.
- Secrets stay in the Brain Cloud environment/secret manager.

Components:
- Brain V12 API: brain_v12.app:app
- Brain Cloud supervisor: cloud/brain_cloud.py
- Cloud control plane: cloud/api_server.py
- Chat UI: brain_v12/web/brain-chat.html

Brain Cloud provides Python 3.11+, ffmpeg, persistent storage and PORT.
