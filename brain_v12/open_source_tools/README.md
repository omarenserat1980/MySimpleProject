# Electronic Brain — Open-Source Tool Hub

This catalog starts a governed discovery/integration layer for open-source tools across:

1. **Boot and virtual machines:** QEMU, EDK II/OVMF, GRUB, U-Boot.
2. **Local AI:** Ollama, llama.cpp, OpenHands, LocalHarness.
3. **Electronic hardware:** KiCad, FreeCAD, OpenOCD, esptool, AVRDUDE, openEMS.

## Read-only discovery

From the repository root:

```bash
python -m brain_v12.tools.open_source_tool_hub
python -m brain_v12.tools.open_source_tool_hub --category local_ai --json
python -m brain_v12.tools.open_source_tool_hub --category boot_virtualization
python -m brain_v12.tools.open_source_tool_hub --category electronics
```

The CLI validates catalog shape and prints metadata only. It deliberately does not install or execute upstream code.

## Integration plan

- **P0 — metadata + provider discovery:** catalog, endpoint checks, health/status reporting.
- **P1 — isolated adapters:** QEMU/OVMF test runs and local inference HTTP providers, only after dependency checks and sandboxing.
- **P2 — specialist tools:** CAD/EDA, embedded build/debug and electromagnetic simulation.
- **Evidence gate:** store tool version, upstream commit/tag, license/SBOM, command line, exit code, logs and artifact hashes.
- **Hardware gate:** programming, flashing, USB/serial access, GPIO, firmware changes, and boot-order changes require an explicit allowlist and per-run approval.
- **Windows boot proof:** only count as successful when a VM has started, the expected disk is attached, guest boot evidence is captured, and the evidence is tied to the same run. A catalog entry is not proof of boot.

## Security and licensing

Upstream code is untrusted until reviewed. Verify each repository's current license and third-party dependency licenses before copying, bundling, or redistributing it. Pin exact versions and hashes; scan dependencies; run tools without administrator/root privileges where possible; sandbox subprocesses; never pass secrets to untrusted tools. Hardware actions must be opt-in and must not be triggered by model-generated commands alone.

This directory records integration candidates. It does **not** claim the listed tools are installed on Arkan, Termux, Render, or any Brain runtime, and does not itself enable Windows Server 2025 provisioning.
