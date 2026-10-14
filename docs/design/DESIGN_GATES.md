# Design Gates

| Gate | Required input | Pass condition | Fail behavior |
|---|---|---|---|
| G0 Discovery | repository/tool inventory | relevant files and constraints identified | stop and report missing context |
| G1 Requirements | requirement list | each mandatory requirement has acceptance criteria | return to specification |
| G2 Architecture | component contracts | dependencies and boundaries reviewed | revise architecture |
| G3 Implementation | approved design | files exist and interfaces match | reject implementation |
| G4 Tests | executable checks | required tests actually pass | preserve logs; block |
| G5 Evidence | artifacts and traceability | claims are supported and correctly classified | downgrade status/block |
| G6 Security | threat/risk review | no unresolved release-blocking issue | block release |
| G7 Physical | RTL/PDK/tool outputs | only claim the specific physical checks passed | block signoff claim |
| G8 Manufacturing | approved fabrication package | external manufacturing evidence where claimed | remain design/package-only |
| G9 Release | reviewed PR and CI | authorized review and checks pass | no automatic merge/deploy |

Gates may be repeated after a change. They cannot be bypassed by changing labels or prompt text.
