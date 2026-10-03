# Brain Runtime Bootstrap

Run this on the machine that will stay online as the Brain Runtime Host.

```bash
export BRAIN_CLOUD_API_KEY='generate-a-long-random-secret'
bash brain_v12/cloud_worker/bootstrap_runtime.sh
```

The script:

1. checks Docker;
2. checks the repository/runtime package;
3. requires an API key;
4. builds and starts the Brain Cloud Worker;
5. performs a real local `/health` check;
6. reports `BRAIN_RUNTIME_READY` only after the check succeeds.

It does **not** create a public endpoint or claim internet availability. A real HTTPS reverse proxy or authorized tunnel is still required before putting an origin into the Brain Web App configuration.
