# Brain Auto Clicker — prototype

Status: offline policy prototype only; no Android taps are performed.

## Safety contract
- Disabled by default.
- Only explicitly allowlisted target IDs can be clicked.
- Per-task click limit is enforced.
- Sensitive-looking actions require explicit approval.
- Each click must be followed by a postcondition check.
- Failed verification or adapter errors disable further clicks.
- Emergency stop blocks execution.
- Audit entries mark `real_device_execution: false` for this prototype.

## Not implemented
Screen capture/OCR, Android AccessibilityService integration, persistent audit storage,
UI discovery, and actual device execution. Do not claim the prototype controls the phone.
