#!/usr/bin/env bash
set -euo pipefail
OUT="${1:-brain-boot-self-trust.iso}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/.brain-iso-build"
rm -rf "$BUILD"
mkdir -p "$BUILD/iso/boot/grub" "$BUILD/iso/brain/runtime" "$BUILD/src"
command -v grub-mkrescue >/dev/null || { echo 'MISSING=grub-mkrescue'; exit 2; }
command -v xorriso >/dev/null || { echo 'MISSING=xorriso'; exit 2; }
command -v gcc >/dev/null || { echo 'MISSING=gcc'; exit 2; }
cat > "$BUILD/src/brain_boot.S" <<'ASM'
.set ALIGN,    1<<0
.set MEMINFO,  1<<1
.set FLAGS,    ALIGN | MEMINFO
.set MAGIC,    0x1BADB002
.set CHECKSUM, -(MAGIC + FLAGS)
.section .multiboot
.align 4
.long MAGIC
.long FLAGS
.long CHECKSUM
.section .text
.global _start
.type _start,@function
_start:
    cli
    mov $0x3f9, %dx
    xor %al, %al
    out %al, (%dx)
    mov $0x3fb, %dx
    mov $0x80, %al
    out %al, (%dx)
    mov $0x3f8, %dx
    mov $0x01, %al
    out %al, (%dx)
    mov $0x3f9, %dx
    xor %al, %al
    out %al, (%dx)
    mov $0x3fb, %dx
    mov $0x03, %al
    out %al, (%dx)
    mov $0x3fc, %dx
    mov $0x03, %al
    out %al, (%dx)
    mov $0x3f9, %dx
    xor %al, %al
    out %al, (%dx)
    mov $message, %esi
1:
    lodsb
    test %al,%al
    jz 2f
    mov %al, %bl
    mov $0x3f8, %dx
    mov %bl, %al
    out %al, (%dx)
    jmp 1b
2:
    hlt
    jmp 2b
.section .rodata
message:
    .asciz "BRAIN-BOOT-1 SELF-TRUST BOOTSTRAP\r\nBRAIN-BOOT-STAGE=1\r\nBRAIN-RUNTIME-HANDOFF=READY\r\n"
ASM
cat > "$BUILD/src/linker.ld" <<'LD'
ENTRY(_start)
SECTIONS {
  . = 1M;
  .text : { *(.multiboot) *(.text) *(.rodata) }
  /DISCARD/ : { *(.eh_frame) *(.comment) }
}
LD
gcc -m32 -ffreestanding -fno-pie -c "$BUILD/src/brain_boot.S" -o "$BUILD/brain_boot.o"
ld -m elf_i386 -T "$BUILD/src/linker.ld" -o "$BUILD/brain_boot.elf" "$BUILD/brain_boot.o"
cp "$BUILD/brain_boot.elf" "$BUILD/iso/boot/brain_boot.elf"
cat > "$BUILD/iso/boot/grub/grub.cfg" <<'CFG'
set timeout=0
set default=0
serial --unit=0 --speed=115200
terminal_input console serial
terminal_output console serial
menuentry 'Electronic Brain Self-Trust Bootstrap' {
  multiboot /boot/brain_boot.elf
  boot
}
CFG
cat > "$BUILD/iso/brain/boot-gate.json" <<'JSON'
{
  "schema": "BRAIN-SELF-TRUST-ISO-1",
  "boot_gate": "BRAIN-SELF-TRUST-GATE-1",
  "bootstrap_capability": "brain_self_test",
  "required_sequence": ["LOCAL_TRUST_ROOT","RUNTIME_READY","AGENT_ONLINE","SELF_TEST_VERIFIED","BRAIN_READY"],
  "failure_status": "BRAIN_BOOT_BLOCKED",
  "kernel": "/boot/brain_boot.elf"
}
JSON
sha256sum brain_v12/app.py brain_v12/brain/self_trust_boot_gate.py > "$BUILD/iso/brain/runtime/source-sha256.txt"
cat > "$BUILD/iso/brain/runtime/runtime-handoff.json" <<'JSON'
{
  "schema": "BRAIN-RUNTIME-HANDOFF-1",
  "stage": 2,
  "runtime_source": "brain_v12",
  "entrypoint": "brain_v12.app:app",
  "launch": "python3 -m uvicorn brain_v12.app:app --host 0.0.0.0 --port 8012",
  "required_before_ready": ["LOCAL_TRUST_ROOT","RUNTIME_READY","AGENT_ONLINE","SELF_TEST_VERIFIED"],
  "ready_status": "BRAIN_READY",
  "bootstrap_status": "BRAIN_BOOTSTRAP_VERIFIED"
}
JSON
cat > "$BUILD/iso/brain/README.txt" <<'TXT'
ELECTRONIC BRAIN BOOT ISO
Stage 1 is a real x86 Multiboot bootstrap and is verified by QEMU serial evidence.
Stage 2 is the runtime handoff contract for the Python Brain source tree.
This image does not falsely claim that Python/Linux/network runtime is already executing.
BRAIN_READY is reserved for the full runtime after the Self-Trust Gate passes.
TXT
grub-mkrescue -o "$OUT" "$BUILD/iso" >/tmp/brain-iso-build.log 2>&1
test -s "$OUT"
sha256sum "$OUT" | tee "$OUT.sha256"
printf 'BRAIN_BOOT_ISO=%s\n' "$OUT"
