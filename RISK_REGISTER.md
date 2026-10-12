# Risk Register — Base Expansion V2

| ID | Risk | Severity | Mitigation | Status |
|---|---|---|---|---|
| R-001 | Existing repository is large and heterogeneous | HIGH | Isolate new foundation and integrate gradually | OPEN |
| R-002 | Foundation accidentally imports Brain | HIGH | Import-boundary tests | MITIGATED_BY_CI |
| R-003 | Architecture grows faster than verification | HIGH | Gate every phase | ACTIVE_GATE |
| R-004 | External dependency lock-in | MEDIUM | Dependency/fallback gate | OPEN |
| R-005 | False success from CI green status | HIGH | Evidence gate + runtime assertions | ACTIVE_GATE |
| R-006 | Migration breaks existing Brain | HIGH | Adapter/parallel test/rollback | OPEN |
| R-007 | Destructive autonomous changes | HIGH | Permissions + rollback + human gates | MITIGATED_IN_MEMORY_ONLY |
| R-008 | Permission grants disappear on restart | HIGH | Keep grants explicitly in-memory; require durable identity design before production | OPEN |
| R-009 | Checkpoints are not durable backups | HIGH | Label checkpoints in-memory; verify persistence and restore separately before production | OPEN |
| R-010 | Retry policy may repeat unsafe side effects | HIGH | Record retryability only; never auto-retry in this phase | MITIGATED |
| R-011 | Exception text may contain sensitive data | HIGH | Failure records store exception type/classification, not raw exception message | MITIGATED_IN_FAILURE_TRACKER |
