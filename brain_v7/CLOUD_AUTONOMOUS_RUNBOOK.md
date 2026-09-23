# Brain V7 cloud autonomous runtime

Brain V7 now has a container entrypoint that runs its continuous autonomous
runtime. A persistent cloud worker must still be created by the owner in a
cloud compute account.

## Deployment
Use a persistent worker service that supports Docker. The container command is
already defined in brain_v7/Dockerfile.

The worker should keep BRAIN_SLEEP_SECONDS at a reasonable value and expose no
public endpoint unless one is intentionally added.

## Secrets
Never commit payment credentials, wallet keys, API tokens, or private keys.
Put secrets in the cloud provider secret/environment store.

## Autonomy boundary
The worker can autonomously research, plan, create, validate, package and learn.
Existing governance and payment gates continue to block unauthorized external
submissions and money movement.

## Emergency stop
Set STOP_BRAIN=1 or create the STOP_BRAIN stop file in the runtime volume.
