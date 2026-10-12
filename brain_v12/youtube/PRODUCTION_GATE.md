# YouTube Production Gate

This gate is the single deterministic decision boundary before Brain spends production resources on a video.

## Required conditions

1. The channel must be viable.
2. The video must pass content selection.
3. Video economics must not return KILL.
4. Candidate and economic records must reference the same video ID.

## Boundary

A successful production gate means only `PRODUCTION_ALLOWED`. It does not mean the video will succeed, be published, be monetized, or generate revenue.

Publishing remains a separate authorization boundary. Confirmed revenue remains a separate Economic Control Plane boundary.

## Orchestration

The gate is pure and side-effect-free. The existing single Brain orchestrator should consume its result rather than creating a new worker or autonomous loop.
