# Design Capability Matrix

Use this table as a live inventory. Update it only with repository/tool/test evidence.

| Domain | Specialist prompt | Typical tools | Minimum evidence | External dependency examples |
|---|---|---|---|---|
| Architecture | 03 | diagrams, dependency scanners | reviewed component map and ADRs | domain review if required |
| Requirements | 02 | schemas, traceability tests | requirement-to-test mapping | stakeholder decisions |
| Software | 05 | Python, linters, unit tests | reproducible test results | APIs/services if explicitly required |
| Digital logic | 06 | Icarus Verilog, Verilator, Yosys | vectors, simulation logs, synthesis reports | toolchain/RTL expertise |
| Physical design | 07 | OpenROAD, PDK, STA/DRC/LVS tools | pinned flow, reports, reviewed outputs | compatible PDK/foundry |
| Simulation | 08 | deterministic local simulators | model assumptions and repeatable results | calibrated reference data |
| Security | 09 | static analysis, secret scanning | findings and remediation evidence | independent security review |
| Verification | 10 | pytest/unittest, formal tools | traceability and passing checks | independent reviewer where needed |
| Infrastructure | 11 | CI, runtime health checks | build/deploy/runtime evidence separated | runner/cloud only if needed |
| Manufacturing | 12 | EDA/CAM tools | approved manufacturing package | physical manufacturer/materials |
| Reliability | 13 | fault injection, recovery tests | bounded recovery and rollback tests | real environment for field claims |
| New domain | 15 | discovered per domain | reviewed prompt, adapter and tests | domain-specific resources |

Initial status for this PR: prompt library and lightweight routing/evidence utilities are proposed implementation. No claim is made that all domains are executable or physically verified.
