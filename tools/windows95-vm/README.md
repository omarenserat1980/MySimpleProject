# Windows 95 QEMU VM for Electronic Brain

This turns a **user-supplied Windows 95 installation ISO** into a QEMU virtual machine with a persistent QCOW2 disk and a browser console (noVNC). It is not the PCjs browser emulator.

## Safety and status

- This folder is a VM recipe, not evidence that a VM has already booted.
- No cloud resources are created by these files. Do not deploy to a paid provider.
- Render Free is not a persistent QEMU/KVM host; this compose file is intended for a Linux host you already control.
- The browser port binds to host loopback only. Do not expose noVNC to the public internet without authentication and TLS.
- Supply installation media you are licensed to use; the project does not download or include Windows 95.
- The VM disk is stored under `./data/windows95.qcow2` and survives container recreation as long as that directory is preserved.

## Start and install

From this directory on a Linux host with Docker Compose:

1. Put your licensed ISO at `media/windows95.iso`.
2. Run `mkdir -p media data` if needed.
3. Run `WIN95_BOOT_MODE=cd docker compose up --build` (the default is `cd`).
4. Open `http://127.0.0.1:6080/vnc.html` on the host. Choose **Connect**.
5. Complete Windows 95 installation and shut down the guest.
6. Restart in disk mode with `WIN95_BOOT_MODE=disk docker compose up --build`. Disk mode boots the existing QCOW2 disk and does not require the ISO to be present.

Defaults are 128 MiB RAM and a 2 GiB virtual disk. The container uses QEMU software emulation (TCG), so it can be slow. Windows 95 installation media and its license are not included.

## Browser access from a phone

For a remote host, keep port 6080 private and access it through an authenticated HTTPS reverse proxy or a secure tunnel. Do not change the compose binding to `0.0.0.0:6080` on an internet-facing host; noVNC is a full desktop control surface.

## Verify

A successful container start is not proof that Windows has booted. Verify the actual guest screen in noVNC and capture a screenshot showing Windows 95 after installation. Until that evidence exists, report status as `NOT_BOOT_VERIFIED`.
