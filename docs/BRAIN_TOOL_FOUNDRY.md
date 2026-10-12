# Brain Tool Foundry — self-building path

## Goal

Give Electronic Brain a repeatable way to design and scaffold tools for itself
using the existing Brain/GitHub development surface, without treating a generated
tool as trusted or executable merely because it was generated.

## Lifecycle

1. **Discover** — inventory the available Brain/GitHub/device/runtime capabilities and identify the missing capability.
2. **Propose** — create a JSON contract: name, purpose, typed inputs/outputs, permissions, and risk notes.
3. **Validate** — run the Tool Foundry schema validator. Unknown fields, permissions, invalid names, duplicate fields, and unsafe paths are rejected.
4. **Scaffold** — generate an inert module, manifest, and README under `brain_v12/generated_tools/<name>/`. Existing files are never overwritten.
5. **Implement** — a code agent proposes the smallest implementation and adds tests; generated code is still untrusted.
6. **Verify** — run static checks, unit tests, dependency/security checks, and relevant Brain smoke tests; attach logs and hashes as evidence.
7. **Review** — create a Git branch and PR. A human reviews permission scope and the implementation. High-impact permissions require explicit approval.
8. **Register** — only after merge and passing evidence, add the tool to the official registry with a narrow permission policy.
9. **Execute** — route calls through the existing supervisor/tool gateway, permission checks, timeouts, audit log, and verification gate.
10. **Learn** — record outcomes and failure evidence; revise the tool through another reviewed PR.

## Current implementation

`brain_v12/brain/tool_foundry.py` implements proposal validation and safe inert
scaffolding. It does **not** generate arbitrary executable logic, run generated
code, edit secrets, self-approve a PR, or register a tool for production.

## Use

Validate a proposal:

```bash
python -m brain_v12.brain.tool_foundry validate proposal.json
```

Scaffold it:

```bash
python -m brain_v12.brain.tool_foundry scaffold proposal.json --root .
```

A proposal JSON shape:

```json
{
  "name": "example_tool",
  "purpose": "A concise statement of the capability to add.",
  "inputs": [{"name": "item_id", "type": "string", "required": true}],
  "outputs": [{"name": "status", "type": "string"}],
  "permissions": ["read"],
  "risk_notes": "No external writes or credentials."
}
```

Allowed permission labels: `read`, `write`, `network`, `secrets`,
`device`, `publish`, `financial`, `destructive`. All but `read` trigger
the human-review flag. The flag is a planning signal, not an authorization grant.

## Acceptance gates

- Tests prove invalid proposals and path traversal are blocked.
- The scaffold is inert (`TOOL_ENABLED = False`) and refuses overwrite.
- Generated code is never auto-imported or auto-executed.
- No production registry change occurs without review and evidence.
- A tool is not marked available until its runtime health check passes.
- Termux-first operation remains supported; missing Termux/device evidence stays
  `BLOCKED` or `WAITING_FOR_TERMUX_AGENT`, never inferred as ready.

## Scope boundaries

This path does not create credentials or GitHub Actions secrets, bypass GitHub
permissions, start offline Desktop Commander devices, or provision paid cloud
resources. Tool-building can be automated; privilege grants and high-impact
actions remain behind explicit authorization.
