# Platform Foundation Architecture — V2

## Boundary
platform_foundation/ is the independent software foundation. It is not Brain and must not import Brain.

## Initial layers
1. Core Runtime
2. Configuration
3. State
4. Execution
5. Audit/Evidence
6. Health

## Initial contracts
Each foundation component must expose explicit inputs, outputs, state, failure behavior, recovery behavior and tests.

## Planned expansion
Configuration -> State -> Jobs/Workers -> API -> Events -> Security/Identity -> Storage -> Observability -> Recovery -> Plugin/Agent runtime.

Only the smallest verified slice is built initially.

## Brain integration
After the platform gate, Brain is connected through explicit adapters. Brain does not become the foundation's hidden dependency.

## Failure boundary
A foundation failure must be observable and must not be converted into synthetic success.
