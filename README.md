# Camplayer v2.0.0

> **Multi IP Camera Viewer — modernized for Raspberry Pi 4/5, CM4/CM5, Docker, and the Web.**

[![CI](https://github.com/iamjairo/camplayer/actions/workflows/ci.yml/badge.svg)](https://github.com/iamjairo/camplayer/actions/workflows/ci.yml)
[![Build OS Image](https://github.com/iamjairo/camplayer/actions/workflows/build-os-image.yml/badge.svg)](https://github.com/iamjairo/camplayer/actions/workflows/build-os-image.yml)
[![Build Tauri App](https://github.com/iamjairo/camplayer/actions/workflows/build-tauri.yml/badge.svg)](https://github.com/iamjairo/camplayer/actions/workflows/build-tauri.yml)
[![Release](https://img.shields.io/github/v/release/iamjairo/camplayer)](https://github.com/iamjairo/camplayer/releases/latest)

![Camplayer grid view](./screenshots/camplayer_nolink.png)

Camplayer turns any Raspberry Pi (or Docker host) into a dedicated IP camera viewing station. View up to 16 RTSP/RTMP/HTTP streams in a configurable grid — no browser plugins, no cloud, no subscription.

---

## What's New in v2.0.0

v2.0.0 is a complete ground-up modernization. The original project was built on OMXplayer and Raspberry Pi OS Buster — both end-of-life. Everything has been rewritten for the current Pi ecosystem.

| Component | Before (v1.x) | After (v2.0.0) |
|---|---|---|
| Video player | OMXplayer (EOL, Buster-only) | **MPV** + JSON IPC |
| OS | Raspberry Pi OS Buster | **Raspberry Pi OS Bookworm** |
| Hardware | Pi 3B only | **Pi 4, Pi 5, CM4, CM5** |
| Hardware decode | VideoCore IV (dispmanx) | **V4L2 M2M / HEVC 4K** |
| Overlay/OSD | pipng (dispmanx, EOL) | **fbi framebuffer** |
| Web interface | None | **React 18 + WebRTC via go2rtc** |
| Configuration UI | Binary blob (closed-source) | **Open-source Textual TUI** |
| Docker support | Partial | **Full stack (go2rtc + API + nginx)** |
| Desktop app | None | **Tauri v2 (macOS/Windows/Linux)** |
| Camera discovery | None | **ONVIF, Hikvision, Reolink, mDNS** |
| Display detection | `tvservice` (removed in Bookworm) | **DRM sysfs** |
| Python | 3.7 | **3.11+** |

---

## Deployment Options

Camplayer v2.0.0 supports three deployment modes. Choose the one that fits your setup.

### 🖥️ Option A — Camplayer OS (Bootable SD Card Image)

The easiest way to get started. Flash a pre-built image to an SD card, plug it into your Pi, and it boots straight into a camera viewer.

1. Download `CamplayerOS-v2.0.0.img.xz` from the [Releases page](https://github.com/iamjairo/camplayer/releases/latest).
2. Flash with [Raspberry Pi Imager](https://www.raspberrypi.com/software/) or `dd`.
3. Before first boot, edit `/boot/camplayer-config.ini` on the FAT32 partition (editable from any PC/Mac/Windows).
4. Boot the Pi — first boot configures WiFi, hostname, timezone and downloads go2rtc automatically.

Configuration files on the FAT32 boot partition:

```
/boot/camplayer-config.ini   ← camera streams and grid layouts
/boot/system-config.ini      ← WiFi, hostname, timezone, display, CEC
```

> **Read-only rootfs:** The OS runs with an overlay filesystem. All writes go to RAM and are lost on reboot — the SD card is protected from corruption. Use `os_readwrite` to temporarily unlock persistent writes, `os_readonly` to re-enable protection.

---

### 🐳 Option B — Docker Compose

Run the full Camplayer stack on any Linux machine or NAS.

**Requirements:** Docker Engine 24+, Docker Compose v2.

```bash
git clone https://github.com/iamjairo/camplayer
cd camplayer

# Edit config before starting
cp config/camplayer-config.ini.example config/camplayer-config.ini
nano config/camplayer-config.ini

docker compose up -d
```

Open your browser at **http://localhost** (or your host IP).

The stack runs three containers:

| Container | Role | Port |
|---|---|---|
| `go2rtc` | RTSP → WebRTC / HLS transcoder | 1984 (internal) |
| `camplayer-api` | FastAPI REST + WebSocket config API | 8000 (internal) |
| `nginx` | Reverse proxy + static frontend | **80** |

---

### 🍓 Option C — Bare Pi Install (Bookworm)

Install directly onto an existing Raspberry Pi OS Bookworm (Lite) system.

```bash
# Requires Raspberry Pi OS Bookworm (arm64 or armhf)
git clone https://github.com/iamjairo/camplayer
cd camplayer
sudo bash install.sh
```

Configure streams:

```bash
nano /home/pi/.camplayer/config.ini
```

Start/enable the service:

```bash
sudo systemctl enable --now camplayer.service
```

---

## Configuration

All three deployment modes use the same `.ini` config format.

### Cameras (DEVICE sections)

```ini
[DEVICE1]
channel1_name = Front Door
channel1.1_url = rtsp://admin:pass@192.168.1.100/stream1   ; main stream
channel1.2_url = rtsp://admin:pass@192.168.1.100/stream2   ; sub stream (lower quality)

[DEVICE2]
channel1_name = Backyard
channel1.1_url = rtsp://admin:pass@192.168.1.101/h264Preview_01_main
channel1.2_url = rtsp://admin:pass@192.168.1.101/h264Preview_01_sub
```

- Section names must be `[DEVICEx]` (x = 1, 2, 3 …)
- Channel URLs follow the pattern `channelN.Q_url` where N = channel number, Q = quality index (1 = main, 2 = sub, up to 9)

### Grid Layouts (SCREEN sections)

```ini
[SCREEN1]
layout = 4
window1 = device1,channel1
window2 = device1,channel1
window3 = device2,channel1
window4 = device2,channel1

[SCREEN2]
layout = 1
window1 = device1,channel1
```

Available layouts:

| Value | Arrangement | Windows |
|:---:|---|:---:|
| `1` | Single full screen | 1 |
| `4` | 2×2 grid | 4 |
| `6` | 1 large + 5 small | 6 |
| `7` | 1 tall + 6 | 7 |
| `8` | 1 large + 7 small | 8 |
| `9` | 3×3 grid | 9 |
| `10` | 2 large + 8 small | 10 |
| `13` | 1 large + 12 small | 13 |
| `16` | 4×4 grid | 16 |

Layout background previews: [`resources/backgrounds/`](./resources/backgrounds/)

### Dual Display (Pi 4 / Pi 5)

Add `display = 2` to any SCREEN section to send it to the second HDMI output:

```ini
[SCREEN1]
display = 2
layout = 9
window1 = device1,channel1
...
```

### Advanced Settings

```ini
[ADVANCED]
showtime      = 30      ; auto-rotate screens every N seconds (0 = off)
loglevel      = 1       ; 0=debug  1=info  2=warning  3=error
buffertime    = 500     ; stream buffer in milliseconds
streamquality = 1       ; 0=lowest  1=auto  2=highest
streamwatchdog = 5      ; broken stream recovery interval in seconds
refreshtime   = 60      ; force-refresh all streams every N minutes
enablehevc    = 1       ; 0=off  1=auto  2=limit FHD  3=force
enableaudio   = 1       ; audio in fullscreen mode (0=off  1=on)
audiovolume   = 80      ; default volume 0–100
screendownscale = 0     ; shrink display area by N% (adds black border)
enablevideoosd = 1      ; show camera name overlay (0=off  1=on)
backgroundmode = 1      ; 0=black  1=static grid  2=dynamic  3=off
screenchangeover = 1    ; 0=normal  1=fast  2=smooth
screenwidth   = 1920    ; override autodetected width
screenheight  = 1080    ; override autodetected height
```

---

## Web Interface

When running in Docker (Option B) or on a Pi with the web stack enabled, open **http://\<host\>** in any browser.

- Live WebRTC streams — no plugins required
- Grid layout switching
- Per-camera settings editor
- Stream quality selection
- Real-time config push (changes take effect without restart)

---

## systemhelper TUI

The `systemhelper` is an open-source terminal configuration tool that replaces the proprietary binary from the original Camplayer OS.

```bash
cd systemhelper
pip install -r requirements.txt
python -m systemhelper
```

Features:
- Dashboard with live stream status
- Camera manager with ONVIF / Hikvision / Reolink auto-discovery
- Layout editor
- Network configuration (WiFi, hostname)
- System settings (timezone, display, audio, CEC)
- Speed test
- HDMI-CEC control

On the OS image it runs automatically at boot as a systemd service and presents the setup TUI on the HDMI console before camplayer starts.

---

## Desktop App (Tauri)

A native desktop app is available for macOS, Windows, and Linux. It connects to any Camplayer instance on your network (local or Docker) and renders the web UI in a native window.

Download from the [Releases page](https://github.com/iamjairo/camplayer/releases/latest):

| Platform | File |
|---|---|
| macOS (Apple Silicon + Intel) | `Camplayer_2.0.0_universal.dmg` |
| Windows | `Camplayer_2.0.0_x64-setup.exe` |
| Linux x86\_64 | `camplayer_2.0.0_amd64.AppImage` |
| Linux ARM64 | `camplayer_2.0.0_aarch64.AppImage` |

The app auto-discovers Camplayer servers via mDNS (`_camplayer._tcp.local`) and always falls back to `camplayer.local` for the OS image.

---

## Hardware Support Matrix

| Hardware | H.264 | H.265/HEVC | 4K | Dual Display | Recommended |
|---|:---:|:---:|:---:|:---:|:---:|
| Raspberry Pi 4 (2GB+) | ✅ | ✅ up to 4K | ✅ | ✅ | ✅ |
| Raspberry Pi 5 | ✅ | ✅ up to 4K | ✅ | ✅ | ✅ |
| Raspberry Pi CM4 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Raspberry Pi CM5 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Raspberry Pi 400 | ✅ | ✅ | ✅ | ❌ | ✅ |
| Raspberry Pi 3B/3B+ | ✅ | ⚠️ limited | ❌ | ❌ | Legacy only |
| Docker (x86\_64) | ✅ | ✅ | ✅ | N/A | ✅ |

Hardware decode uses V4L2 M2M on Pi 4/5. The `hwdec` method is auto-detected at startup.

---

## Key Bindings (Pi / headless mode)

```
space               Pause/resume automatic screen rotation
enter               Toggle grid ↔ single (zoom) view
left / right        Previous / next screen (or camera in single view)
up / down           Increase / decrease stream quality
1–16                Jump to camera N in single view
0 / escape          Return to grid view
q                   Quit
```

---

## Security Notes

- RTSP and HTTP streams transmit credentials in plain text — use a dedicated VLAN for cameras.
- Config files store usernames and passwords as plain text. Restrict file permissions.
- Disable SSH or change the default password on the Pi if not needed.
- The web interface has no authentication by default — do not expose it to the public internet.

---

## Project Structure

```
camplayer/          Python core (MPV player, window manager, stream watchdog)
web/
  backend/          FastAPI REST API + go2rtc config sync
  frontend/         React 18 + Vite + TailwindCSS web UI
systemhelper/       Textual TUI — open-source replacement for the original binary
os/                 pi-gen stage for building the bootable OS image
tauri-app/          Tauri v2 native desktop app
config/             Default .ini config files
resources/          Layout background images, icons
.github/workflows/  CI, OS image build, Tauri multi-platform build
docs/legacy/        Original README and pre-v2 documentation
```

---

## Building from Source

### Web frontend
```bash
cd web/frontend
npm ci
npm run build
```

### systemhelper
```bash
cd systemhelper
pip install -r requirements.txt
python -m systemhelper
```

### Tauri desktop app
```bash
cd tauri-app
npm ci
npm run tauri build
```

### OS image (requires Linux + Docker)
```bash
cd os
bash build.sh
```

---

## Contributing

Pull requests welcome. Please run the existing checks before submitting:

```bash
# Python syntax check
python -m py_compile camplayer/**/*.py systemhelper/**/*.py

# TypeScript check
cd web/frontend && npx tsc --noEmit
cd tauri-app && npx tsc --noEmit
```

---

## License

MIT — see [LICENSE](./LICENSE).

> **Historical context:** The original Camplayer was built around OMXplayer and Raspberry Pi OS Buster (both EOL). The pre-v2 README and documentation have been preserved in [`docs/legacy/`](./docs/legacy/) for reference.
