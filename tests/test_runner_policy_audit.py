from pathlib import Path
from brain_v12.runner_policy_audit import audit_workflows


def test_base_expansion_workflows_are_brain_owned():
    findings = audit_workflows(Path("."))
    assert findings == [], "\n".join(findings)
