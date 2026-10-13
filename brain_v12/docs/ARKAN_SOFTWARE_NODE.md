# Canonical Arkan Software Node

The canonical Arkan target is `arkan-virtual-01`, a software-only Brain node.
It hosts the Brain-managed `DesktopCommanderEmulator` and `PowerShellEmulator`
applications. The orchestration layer must call this node facade rather than
invoking native Desktop Commander or a host PowerShell session directly.

## Contract

- `node_type=SOFTWARE_ONLY`
- `physical_host_required=false`
- `native_desktop_commander_used=false`
- `native_powershell_used=false`
- `reality=SIMULATED`
- `execution_eligible=false` for real-world or production work
- emulator filesystem operations are confined to the node sandbox
- the PowerShell emulator interprets a supported subset of commands and never launches powershell.exe
- a simulated VM record is not evidence of a booted Windows Server guest

## Use

```python
from brain_v12.brain.arkan_software_node import ArkanSoftwareNode

node = ArkanSoftwareNode("~/.brain/nodes/arkan-virtual-01")
state = node.connect()
print(state)
print(node.run_powershell("Write-Output hello; Get-ComputerInfo"))
```

The software node is usable for simulations, tests, orchestration development, and
repeatable app-level workflows. It does not establish connectivity to a physical
Arkan computer or claim that Windows Server 2025 is running. Production/real
execution must remain blocked unless a separately approved execution provider and
fresh evidence are explicitly configured.
