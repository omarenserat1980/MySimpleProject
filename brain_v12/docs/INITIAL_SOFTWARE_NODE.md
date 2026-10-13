# Electronic Brain — Initial Software Node

**Node ID:** `brain-software-node-01`  
**Schema:** `electronic-brain.initial-software-node.v1`

This is the first generic, software-only node prototype. It is deliberately not
named after or attached to Arkan, a phone, a PC, or a physical executor.

## Included

- Start/stop lifecycle and local heartbeat sequence.
- Allowlisted task types: `health_check`, `write_text`, and `read_text`.
- A workspace sandbox with path traversal and symlink-escape protection.
- A bounded virtual hardware bundle: BrainVM-1 CPU interpreter, sparse logical RAM with ECC model, quota-enforced workspace storage, and an in-memory NIC/switch topology.
- A BrainVM program task and an isolated virtual-network self-test.
- GPU capability is explicitly unavailable; no physical GPU or acceleration is claimed.
- Explicit status fields declaring that physical hosts, network I/O, shell
  execution, external resource creation, and real Windows boot are not enabled.

## Not included

This node is not a cloud VM, persistent remote agent, general-purpose shell, or
Windows Server 2025 hypervisor. The CPU executes only the BrainVM-1 tuple ISA, not
x86/ARM machine code. RAM capacity is measured in sparse addressable cells rather
than reserved host bytes. Storage is a local workspace with a configured quota.
The virtual network never opens host sockets. GPU is unavailable. Its workspace and heartbeat are local process
state. It does not download an ISO, provision cloud infrastructure, open a port,
or claim a real boot.

## Quick start

```python
from brain_v12.brain.initial_software_node import InitialSoftwareNode

node = InitialSoftwareNode("./.brain/software-node")
print(node.start())
print(node.heartbeat())
print(node.execute({"type": "health_check"}))
print(node.execute({"type": "network_self_test"}))
node.stop()
```

## Test

```bash
PYTHONPATH=. python -m unittest brain_v12.tests.test_initial_software_node -v
```

A successful test validates this isolated software contract only. Real Windows
Server 2025 boot still requires a separately authorized, available execution host
and guest-origin evidence.
