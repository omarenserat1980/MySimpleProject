"""Integration patch guidance for BrainSupervisor pathway evaluation.

The canonical implementation is added directly to brain_supervisor.py in the
pathway engine pull request. This file intentionally provides a no-op marker
for audit tooling only and is not imported at runtime.
