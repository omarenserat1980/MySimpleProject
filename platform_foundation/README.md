# Platform Foundation

This directory is the independent Base Expansion foundation.

It intentionally does not import `brain_v12`.

The first slice proves only a minimal real runtime contract:

- start/stop
- state set/get/snapshot/restore
- job registration/execution/failure capture
- append-only evidence events
- health reporting

This is not yet the full platform. More layers are gated behind verification.
