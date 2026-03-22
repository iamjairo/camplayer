# Camplayer – Copilot Instructions

## What This Project Is

**Camplayer** is a multi-IP-camera viewer for Raspberry Pi. It reads an INI config file, opens one OMXplayer subprocess per camera stream, and composites them into a grid layout on the HDMI display. It also runs in a Docker container.

**Current status:** The project is on life support. It targets Raspberry Pi 3B + Raspberry Pi OS Buster — both of which are EOL. The primary video backend (`omxplayer`) was removed from Pi OS after Bullseye and only works on VideoCore IV (Pi 3 and older). **This codebase is actively being modernized** — see the Upgrade Direction section below.

---

## Running the App

```bash
# Demo mode (no config file needed, uses bundled demo videos)
camplayer --demo

# With default config (~/.camplayer/config.ini)
camplayer

# With explicit config
camplayer -c /path/to/config.ini

# Rebuild stream metadata cache
camplayer --rebuild-cache
```

### Install

```bash
sudo sh ./install.sh
```

Installs to `/usr/local/share/camplayer/`, registers a systemd service, and builds the `pipng` background renderer from source.

### Service

```bash
sudo systemctl start camplayer.service
sudo systemctl status camplayer.service
journalctl -u camplayer.service -f
```

---

## Testing

There are no automated unit tests. Testing is manual using the INI configs in `tests/`:

```bash
# Run with a specific test scenario
camplayer -c tests/test-audio-config.ini
camplayer -c tests/test-hevc-config.ini
camplayer -c tests/test-performance_360pH264-config.ini
```

Each file in `tests/` exercises a specific scenario (codec, resolution, dual-screen, audio, etc.) using demo video files from `resources/video/`.

---

## Architecture

### Component Map

```
camplayer.py          ← Entry point, main loop, keyboard events, signal handlers
  └─ ScreenManager    ← Manages multiple Screen instances, auto-rotation timer
       └─ Screen      ← One display + layout (e.g. 2x2 grid); owns Window list
            └─ Window ← One OMXplayer subprocess; D-Bus control, PLAYSTATE tracking
                └─ StreamInfo  ← FFprobe analysis: codec, resolution, fps, audio

backgroundgen.py      ← Renders grid overlay images via pipng (a custom C library)
utils/inputhandler.py ← Threaded evdev keyboard monitor, thread-safe event queue
utils/settings.py     ← INI config loader; defines LAYOUT, CHANGEOVER, STREAMQUALITY enums
utils/constants.py    ← Paths, hardware limits, D-Bus timeouts, KEYCODE scan codes
utils/globals.py      ← Mutable runtime flags (VLC/ffmpeg support, Pi model, HEVC)
utils/logger.py       ← LOG class with LOGLEVEL enum (DEBUG/INFO/WARNING/ERROR)
utils/utils.py        ← Pi hardware detection, GPU memory, display mode, process mgmt
```

### Main Loop (camplayer.py)

Each 0.1s cycle:
1. `screenmanager.do_work()` — advance all window state machines
2. `keyboard.get_events()` — drain input queue
3. Dispatch key actions (screen switch, quality up/down, fullscreen, quit)

### Window Playback State Machine

```
NONE → INIT1 → INIT2 → PLAYING
                  ↓        ↓
               BROKEN ←────┘   (watchdog detects stall → restart)
```

### Config File Structure

```ini
[DEVICE1]
channel1_name   = Front Door
channel1.1_url  = rtsp://user:pass@192.168.1.10/stream1   # sub-stream 1
channel1.2_url  = rtsp://user:pass@192.168.1.10/stream2   # sub-stream 2 (higher quality)

[SCREEN1]
layout   = 4          # 1=1x1, 4=2x2, 9=3x3, 16=4x4, 6=1P5, 8=1P7, etc.
display  = 1
window1  = device1,channel1
window2  = device1,channel2

[ADVANCED]
loglevel       = 1    # 0=debug 1=info 2=warn 3=error
buffertime     = 500  # ms
streamquality  = 1    # 0=low 1=auto 2=high
enablehevc     = 1    # 0=off 1=auto 2=FHD 3=4K
streamwatchdog = 15   # recovery check interval (sec)
screenchangeover = 1  # 0=normal 1=prebuffer 2=smooth
```

---

## Key Conventions

### Static Class Pattern
Most utility classes use `@classmethod` / `@staticmethod` throughout — they act as singletons without instantiation:
```python
CONFIG.load()           # not CONFIG().load()
LOG.message(...)
CONSTANTS.CONFIG_PATH
GLOBALS.PI_MODEL
```

### Logging
Always use the `LOG` facade, never `print()`:
```python
from .utils import logger
_LOG_NAME = "MyModule"   # module identifier, defined at top of each file
logger.log_message(_LOG_NAME, logger.LOGLEVEL.INFO, "message")
```

### Sentinel Values
`-1` (`_IDX_NOT_SET`) is the standard unset-index sentinel throughout window and screen indexing.

### Stream Quality / Weight System
Each stream gets a `weight` (resolution × fps normalized) tracked against `CONSTANTS.MAX_DECODER_WEIGHT`. The AUTO quality mode uses this to stay within GPU limits. When adding new player backends, preserve this weight tracking.

### D-Bus Player Control
OMXplayer is controlled via `dbus-send` subprocesses to `org.mpris.MediaPlayer2.omxplayer.instancePID`. The replacement (MPV) uses a JSON IPC socket — same concept, different transport.

---

## Camplayer OS (the .img)

The original Camplayer OS (`CAMPLAYER_OS_BETA_GENERIC_20210427.img`) has three components:

1. **Camplayer** — this repo's Python code, installed to `/usr/local/share/camplayer/`
2. **OS** — hardened Debian Buster with: read-only root filesystem (`overlayfs`), boot-partition config (FAT32 `/boot/camplayer-config.ini` + `system-config.ini` — user-editable by inserting SD card into any PC), HDMI-CEC scripts (`cec_start/stop_camplayer`), 1920×1080 PNG splash screens, `fake-hwclock`
3. **Systemhelper** — closed-source proprietary binary (PyInstaller-compiled ARM Python). Runs as a systemd service. Uses `npyscreen` (terminal forms UI over HDMI), `evdev` (keyboard nav), `hikvisionapi` + `xmltodict` (camera discovery), `speedtest-cli`. The config UI appears directly on the TV — no SSH needed. Writes merged config to `/dev/shm/camplayer-config.ini`; the camplayer service reads from RAM.

**Config flow:** `/boot/camplayer-config.ini` → systemhelper → `/dev/shm/camplayer-config.ini` → camplayer service

---

## Camplayer 2.0 — Modernization Roadmap

This is an active full-stack modernization. All five phases are planned; work proceeds phase by phase.

### Target Architecture

```
IP Cameras (RTSP/HTTP)
        │
    [go2rtc]  ← RTSP→WebRTC relay; H265→H264 transcode for browsers
    │       │
[MPV]   [WebRTC/HLS]
    │       │
[HDMI]  [React web UI]──── http://camplayer.local ────[Tauri app]
        │
    [FastAPI backend]  ← config, layout, stream health, auth
        │
    [Systemhelper 2.0] ← Textual TUI (on TV) + embeds FastAPI
        │
    /boot/camplayer-config.ini  ← still SD-card-editable
```

### Repo Structure (target monorepo)
```
camplayer/          ← Python core (modernized, Phase 1)
web/
  backend/          ← FastAPI (Phase 2)
  frontend/         ← React (Phase 2)
systemhelper/       ← open-source Textual TUI + embedded API (Phase 3)
os/
  stage-camplayer/  ← pi-gen Bookworm stage (Phase 4)
tauri/              ← Tauri v2 desktop app (Phase 5)
docker-compose.yml  ← go2rtc + api + nginx
.github/workflows/  ← CI + pi-gen image build
```

### Phase 1 — Core: Pi 4/5 Native Display
| What | Old → New |
|---|---|
| Video player | `omxplayer` → **MPV** `--hwdec=v4l2m2m` |
| Player IPC | D-Bus (`dbus-send`) → **MPV JSON IPC socket** (`--input-ipc-server`) |
| Background compositor | `pipng` (VideoCore IV only) → **SDL2 or DRM/KMS overlay** |
| OS target | Buster → **Bookworm (Debian 12)** |
| Hardware | Pi 3B → **Pi 4B / Pi 5 / CM4 / CM5** |
| Python | 3.7 → **3.11+** |

### Phase 2 — Web: Browser Viewing + Docker
- **go2rtc** sidecar: auto-configured from existing INI, handles all codec/protocol negotiation
- **FastAPI** backend: REST API for config (GET/PUT), stream status (WebSocket), layout switching
- **React** frontend: grid layout matching `LAYOUT` enum as CSS grid, WebRTC `<video>` cells
- **Docker Compose**: `go2rtc` + `camplayer-api` + `nginx`
- **`camplayer.local`** via avahi mDNS

### Phase 3 — Systemhelper 2.0 (open source)
- **Textual** TUI (replaces npyscreen) — same TV-based keyboard-driven config UI
- **Camera discovery**: ONVIF (`python-onvif-zeep`), Hikvision, Reolink (`reolink-aio`), Dahua
- **HDMI-CEC**: `python-cec`, TV power → start/stop camplayer
- Embeds the FastAPI backend so `http://camplayer.local` served by systemhelper process

### Phase 4 — Camplayer OS Image (pi-gen)
- **Base**: Bookworm Lite, arm64, targets Pi 4B / Pi 5 / CM4 / CM5
- **Read-only rootfs**: `overlayfs` + tmpfs for `/dev/shm`, `/tmp`
- **Boot-partition config**: keep `/boot/camplayer-config.ini` + `system-config.ini` design
- **Plymouth splash**: 1920×1080 boot + halt screens
- **CI**: GitHub Actions → `.img.xz` artifact on tag

### Phase 5 — Tauri v2 Desktop App
- Wraps the React web frontend (Phase 2)
- mDNS auto-discovery of `camplayer.local`; manual IP entry for remote servers
- Native keyboard shortcuts mapping existing `KEYCODE` constants (replaces `evdev` in desktop mode)
- Fullscreen/kiosk mode; cross-platform: Linux/ARM, x86, Windows, macOS

### What to Preserve Across All Phases
- INI config format and key names — user-facing API compatibility
- `LAYOUT` enum values — map 1:1 to CSS grid templates
- `STREAMQUALITY` AUTO logic and decoder weight system
- `PLAYSTATE` state machine (NONE → INIT1 → INIT2 → PLAYING → BROKEN)
- Stream watchdog and recovery pattern
- `/boot` partition config design (SD-card editable)
- Read-only rootfs (OS reliability feature)

### Codec Notes
- H.265 in browsers: Safari decodes natively; Chrome/Firefox do not — go2rtc transcodes to H.264 for WebRTC when needed
- Pi 5: VideoCore VII adds AV1 hardware decode
- Pi 4/5 H.264/H.265 hardware decode via `v4l2m2m` (V4L2 kernel driver)

---

## File Locations

| Purpose | Path |
|---|---|
| Default config | `~/.camplayer/config.ini` |
| Stream metadata cache | `~/.camplayer/cache/` |
| Installed app | `/usr/local/share/camplayer/` |
| Executable | `/usr/local/bin/camplayer` |
| Resources (icons, backgrounds, demo video) | `resources/` |
| Example configs | `examples/` |
| Test scenario configs | `tests/` |
