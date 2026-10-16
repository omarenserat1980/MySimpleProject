#!/usr/bin/env python3
"""Read-only diagnostic for Electronic Brain V12 device-bridge auth readiness.

This tool never prints secret values, creates keys, edits configuration, or enables
device execution. A present environment variable is only a local hint; it does
not prove the deployed Brain service has valid authentication configured.
"""
from __future__ import annotations

import json
import os
import sys

# Common deployment names used by Brain/device-agent integrations. Keep this
# list explicit so the doctor never dumps the process environment.
CANDIDATES = (
    "BRAIN_DEVICE_AGENT_KEY",
    "V12_AGENT_KEY",
    "DEVICE_AGENT_KEY",
    "BRAIN_DEVICE_BRIDGE_TOKEN",
    "DEVICE_BRIDGE_TOKEN",
)

def main() -> int:
    present = [name for name in CANDIDATES if bool(os.environ.get(name, "").strip())]
    report = {
        "tool": "brain-device-auth-doctor",
        "mode": "read-only",
        "secret_values_printed": False,
        "candidate_variables_checked": list(CANDIDATES),
        "variables_present": present,
        "variables_missing": [name for name in CANDIDATES if name not in present],
        "local_auth_hint": "candidate_present" if present else "no_candidate_present",
        "deployment_verified": False,
        "device_execution_enabled_or_changed": False,
        "next_step": (
            "Compare the deployed service's documented auth variable name with its "
            "secret-presence status; configure it only through the authorized secret "
            "manager, then run an authenticated health/probe check."
            if not present else
            "Confirm which variable the deployed service actually consumes, then run "
            "an authenticated health/probe check. Presence alone is not proof."
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
