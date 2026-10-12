# Open-source tool preflight

Electronic Brain now has a non-invasive local availability probe for its optional open-source tool catalog.

Run from the repository root:

```bash
python -c "from brain_v12.tools.open_source_tool_preflight import inspect_tool_availability; import json; print(json.dumps(inspect_tool_availability(), indent=2))"
```

The probe only searches the current process `PATH` for known executable names. It does not run the discovered programs, check network endpoints, install dependencies, download repositories, create VMs, or access attached hardware. A result of `available` means only that an executable path was found; it is not a version, health, or boot-success check.

Windows boot evidence still requires an authorized execution contract and evidence collected from the actual VM boot. This preflight cannot prove Windows Server installation or boot.
