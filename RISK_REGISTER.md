# Risk Register — Base Expansion V2

| ID | Risk | Severity | Mitigation | Status |
|---|---|---|---|---|
| R-001 | Existing repository is large and heterogeneous | HIGH | Isolate new foundation and integrate gradually | OPEN |
| R-002 | Foundation accidentally imports Brain | HIGH | Import-boundary tests | OPEN |
| R-003 | Architecture grows faster than verification | HIGH | Gate every phase | OPEN |
| R-004 | External dependency lock-in | MEDIUM | Dependency/fallback gate | OPEN |
| R-005 | False success from CI green status | HIGH | Evidence gate + runtime assertions | OPEN |
| R-006 | Migration breaks existing Brain | HIGH | Adapter/parallel test/rollback | OPEN |
| R-007 | Destructive autonomous changes | HIGH | Permissions + rollback + human gates | OPEN |
