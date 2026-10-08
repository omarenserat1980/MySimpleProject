# Video Economics Engine

The engine evaluates whether producing a video is economically sensible before production resources are consumed.

## Inputs

- production hours
- direct tool and asset costs
- expected views
- estimated RPM
- probability of success
- learning value

## Decisions

PRODUCE: positive expected value under the configured cost gate.

HOLD: weak or absent monetary signal but meaningful learning value.

KILL: excessive direct cost or weak expected value without sufficient learning value.

## Critical financial boundary

Expected ad value, expected net value, RPM, break-even views, and learning value are forecasts. They are never confirmed revenue and never update the Economic Ledger.

Only the existing Economic Control Plane can settle confirmed revenue after valid payment evidence and complete causality.

## Operating principle

The engine is deterministic and side-effect-free. The single Brain orchestrator decides when to act on its output.
