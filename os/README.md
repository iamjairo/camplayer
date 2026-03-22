# Camplayer OS — Build Guide

## Overview

`os/` contains a **pi-gen custom stage** that builds a complete, bootable
`CamplayerOS-bookworm-arm64.img.xz` for Raspberry Pi 4B, 5, CM4, and CM5.

The image is based on **Raspberry Pi OS Bookworm Lite (64-bit)** with:

| Feature | Detail |
|---|---|
| Player | MPV with DRM/KMS (no X11, no Wayland) |
| Streams | RTSP / WebRTC via go2rtc |
| Web UI | React frontend + Python FastAPI backend |
| Root FS | Read-only overlayfs (tmpfs upper layer) |
| mDNS | `camplayer.local` via Avahi |
| Boot config | Edit `camplayer-config.ini` / `system-config.ini` from any PC |

---

## Prerequisites

### Docker host (recommended — cross-compiles on any x86 machine)
```bash
sudo apt-get install -y docker.io docker-compose
```

### Native Debian/Raspberry Pi host
```bash
sudo apt-get install -y coreutils quilt parted qemu-user-static debootstrap \
  zerofree zip dosfstools libarchive-tools libcap2-bin grep rsync xz-utils \
  file git curl bc xxd kmod binfmt-support
```

Node.js ≥ 20 is also required to build the React frontend:
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt-get install -y nodejs
```

---

## Build

```bash
# Standard build (clean)
./os/build.sh

# Incremental build (reuse pi-gen cache)
./os/build.sh --no-clean
```

The build script:
1. Clones `pi-gen` (arm_bookworm branch) to `/tmp/pi-gen`
2. Copies `os/stage-camplayer` and the entire repo source into pi-gen
3. Runs `stage0 → stage1 → stage2 → stage-camplayer`
4. Outputs `CamplayerOS-<date>-bookworm-arm64.img.xz` to `/tmp/pi-gen/deploy/`

Build time: ~30–60 min on a modern x86 host with QEMU.

---

## Stage breakdown

| Stage | Purpose |
|---|---|
| `stage0` | Minimal Debian Bookworm bootstrap (pi-gen built-in) |
| `stage1` | Core Raspberry Pi OS packages (pi-gen built-in) |
| `stage2` | Lite image base — no desktop (pi-gen built-in, images skipped) |
| `stage-camplayer/00-packages` | Install mpv, ffmpeg, avahi, cec-utils, etc. |
| `stage-camplayer/01-camplayer-install` | Install Camplayer app, services, configs |
| `stage-camplayer/02-readonly-rootfs` | Configure overlayfs read-only root |
| `stage-camplayer/03-plymouth-splash` | Install dark text boot splash |

---

## Flash

### balenaEtcher (GUI, any OS)
1. Download [balenaEtcher](https://etcher.balena.io/)
2. Select the `.img.xz` file (Etcher decompresses automatically)
3. Select your SD card or USB drive
4. Click Flash

### `dd` (Linux / macOS)
```bash
xzcat CamplayerOS-*.img.xz | sudo dd of=/dev/sdX bs=4M status=progress
```
Replace `/dev/sdX` with your SD card device (use `lsblk` to identify it).

---

## First boot

On first boot, `camplayer-firstboot.service` runs automatically and:

1. **Applies hostname** from `system-config.ini`
2. **Configures WiFi** (if `wifi_ssid` is set in `system-config.ini`)
3. **Sets timezone** from `system-config.ini`
4. **Patches `/boot/cmdline.txt`** to add quiet/splash boot params
5. **Downloads go2rtc** binary from GitHub releases (requires internet)
6. **Disables itself** so it never runs again

First boot takes about 60–90 seconds. The screen will be blank during
go2rtc download. Subsequent boots are fast.

---

## Editing config from a PC

Insert the SD card into any computer. The first (FAT32) partition is readable
on Windows, macOS, and Linux. Edit either file with any text editor:

- **`camplayer-config.ini`** — cameras, layouts, stream URLs
- **`system-config.ini`** — WiFi, hostname, timezone, CEC settings

Changes take effect on the next reboot.

---

## Making persistent changes

The root filesystem is **read-only by default** (overlayfs + tmpfs upper layer).
Changes made at runtime are lost on reboot.

To make persistent changes to the root filesystem:

```bash
# On the Pi, SSH in or use the console:
os_readwrite        # Remounts rootfs read-write (changes persist to SD)

# Make your changes...

os_readonly         # Remount read-only again when done
```

---

## Default credentials

| Item | Value |
|---|---|
| Username | `pi` |
| Password | `camplayer` |
| SSH | Enabled on port 22 |
| Web UI | http://camplayer.local |
| mDNS hostname | `camplayer.local` |

**Change the password** after first boot:
```bash
os_readwrite
passwd pi
os_readonly
```

---

## Shrinking the image

After building, you can further reduce image size with PiShrink:

```bash
# Decompress first
xz -d CamplayerOS-*.img.xz

# Shrink
./os/shrink-image.sh CamplayerOS-*.img
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Blank screen after boot | Check `/boot/config.txt` — ensure `dtoverlay=vc4-kms-v3d` is present |
| go2rtc not starting | Check `journalctl -u camplayer-go2rtc` — may need internet on first boot |
| WiFi not connecting | Verify `wifi_ssid`/`wifi_password` in `system-config.ini`; country code must match |
| Can't SSH in | Ensure `ENABLE_SSH=1` was set during build (it is by default) |
| Services not starting | `journalctl -b -u camplayer-systemhelper` for logs |
| Read-only errors | Run `os_readwrite` before making changes |
