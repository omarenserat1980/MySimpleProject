#!/usr/bin/env bash
set -euo pipefail
OUT="${1:-brain-boot-self-trust.iso}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/.brain-iso-build"
rm -rf "$BUILD"
mkdir -p "$BUILD/iso/boot/grub" "$BUILD/iso/brain" "$BUILD/src"
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
    mov $message, %esi
    mov $0xb8000, %edi
1:
    lodsb
    test %al,%al
    jz 2f
    mov %al, %bl
    movb $0x0f,(%edi)
    inc %edi
    movb %bl,(%edi)
    inc %edi
    mov $0xe9, %dx
    mov %bl, %al
    out %al, (%dx)
    jmp 1b
2:
    hlt
    jmp 2b
.section .rodata
message:
    .asciz "BRAIN-BOOT-1 SELF-TRUST BOOTSTRAP"
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
cat > "$BUILD/iso/brain/README.txt" <<'TXT'
ELECTRONIC BRAIN BOOT ISO
This image contains a real x86 Multiboot bootstrap kernel and the Brain Self-Trust Gate contract.
The bootstrap kernel proves ISO execution; it does not pretend to be the full Python Brain runtime.
The runtime becomes BRAIN_READY only after the self-trust evidence gate passes.
TXT
grub-mkrescue -o "$OUT" "$BUILD/iso" >/tmp/brain-iso-build.log 2>&1
test -s "$OUT"
sha256sum "$OUT" | tee "$OUT.sha256"
printf 'BRAIN_BOOT_ISO=%s\n' "$OUT"
