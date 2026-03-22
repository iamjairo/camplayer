# Camplayer Systemhelper

Open-source replacement for the proprietary closed-source `systemhelper` binary
that shipped with the original Camplayer OS image. Provides a full **Textual TUI**
for on-screen TV configuration and embeds the **FastAPI web API** so
`http://camplayer.local:8000` works simultaneously.

---

## What it does

The original `systemhelper` was a PyInstaller-compiled ARM binary that rendered
a terminal config UI on `/dev/tty1`. This replacement provides the same
functionality in transparent, auditable Python:

| Feature | Implementation |
|---|---|
| Terminal TUI on TV | Textual framework (keyboard-navigable on `/dev/tty1`) |
| Web config UI backend | FastAPI (re-used from `web/backend/`) |
| Camera discovery | ONVIF WS-Discovery + Hikvision ISAPI + Reolink HTTP API |
| WiFi configuration | Writes `/etc/wpa_supplicant/wpa_supplicant.conf` + `wpa_cli reconfigure` |
| Hostname / mDNS | `hostnamectl` + avahi-daemon |
| Timezone | `timedatectl set-timezone` |
| HDMI-CEC | `cec-client` subprocess (no python-cec binary dependency) |
| Speed test | `speedtest-cli --json` |
| Config persistence | `/boot/camplayer-config.ini` + `/boot/system-config.ini` |

---

## Keyboard Navigation

| Key | Action |
|-----|--------|
| `1` | Dashboard (home) |
| `2` | Camera Manager |
| `3` | Layout Editor |
| `4` | Network |
| `5` | System Settings |
| `6` | HDMI-CEC |
| `7` | Speed Test |
| `↑ ↓ ← →` | Navigate within a screen |
| `Enter` | Select / activate |
| `Tab` | Move focus to next widget |
| `Esc` | Go back / close dialog |
| `q` | Quit systemhelper |

---

## Config Files

### `/boot/camplayer-config.ini`

Main camera and layout configuration. Lives on the FAT32 boot partition so it
can be edited by inserting the SD card into any PC.

```ini
[DEVICE1]
channel1_name = Front Door
channel1.1_url = rtsp://admin:pass@192.168.1.10/Streaming/Channels/101
channel1.2_url = rtsp://admin:pass@192.168.1.10/Streaming/Channels/102

[SCREEN1]
display = 1
layout = 9
window1 = device1,channel1
window2 = device2,channel1

[ADVANCED]
stream_quality = 1
changeover_type = 1
background = 1
hevc_mode = 1
audio_mode = 0
screen_changeover_time = 0
```

**Layout values:** `1`=Single, `4`=2×2, `6`=PiP 1+5, `7`=PiP 3+4, `8`=PiP 1+7,
`9`=3×3, `10`=PiP 2+8, `13`=PiP 1+12, `16`=4×4

### `/boot/system-config.ini`

Hardware and OS-level settings (reverse-engineered from Camplayer OS image):

```ini
[SYSTEM]
wifi_ssid = MyNetwork
wifi_password = secret
wifi_country = US
hostname = camplayer
display_width = 1920
display_height = 1080
display_rotate = 0
timezone = America/New_York
cec_enabled = true
cec_standby = true
cec_wakeup = true
audio_output = hdmi
auto_update = false
```

### Config flow

```
/boot/camplayer-config.ini
        │
        ▼  (systemhelper reads + writes)
/dev/shm/camplayer-config.ini   ← runtime copy (camplayer service reads this)
        │
        ▼
go2rtc.yaml                     ← auto-generated from config
```

---

## Camera Discovery

Systemhelper can auto-discover cameras on your LAN:

1. **Ping sweep** — TCP connect to ports 80/554/8080 for all 254 hosts in the
   local /24 subnet (no root/ICMP required, 50 concurrent connections)
2. **Hikvision ISAPI** — `GET /ISAPI/System/deviceInfo` with digest auth
3. **Reolink HTTP API** — `POST /api.cgi?cmd=GetDevInfo`
4. **ONVIF WS-Discovery** — UDP multicast to `239.255.255.250:3702` +
   `GetProfiles` / `GetStreamUri` SOAP calls (no python-onvif library needed)

---

## Running

### Standalone (development)

```bash
cd /path/to/camplayer
CAMPLAYER_CONFIG=config/camplayer-config.ini \
  python3 -m systemhelper
```

The TUI opens in the current terminal. The FastAPI backend starts on port 8000.

### As a systemd service

```bash
# Copy files
sudo cp -r systemhelper /usr/local/share/camplayer/
sudo cp systemhelper/camplayer-systemhelper.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable camplayer-systemhelper
sudo systemctl start camplayer-systemhelper

# View logs
journalctl -u camplayer-systemhelper -f
```

The service runs as user `pi` with `WorkingDirectory=/usr/local/share/camplayer`.

### On the TV display (`/dev/tty1`)

To force the TUI to render on the HDMI TV output, run via:

```bash
sudo -u pi TERM=linux python3 -m systemhelper < /dev/tty1 > /dev/tty1 2>&1
```

Or set `StandardInput=tty` and `TTYPath=/dev/tty1` in the systemd unit.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMPLAYER_CONFIG` | `/boot/camplayer-config.ini` | Path to main camplayer config |
| `GO2RTC_URL` | `http://localhost:1984` | go2rtc API base URL |

---

## Dependencies

Install with:

```bash
pip3 install -r systemhelper/requirements.txt
```

| Package | Purpose |
|---------|---------|
| `textual` | TUI framework |
| `fastapi` + `uvicorn` | Embedded web API |
| `pydantic` | Config models |
| `httpx` | Async HTTP for camera discovery |
| `ruamel.yaml` | go2rtc.yaml generation |
| `watchdog` | Config file change detection |
| `speedtest-cli` | Network speed test |

### System dependencies (Raspberry Pi OS)

```bash
sudo apt install cec-client ffmpeg avahi-daemon wpasupplicant
```

---

## Architecture

```
systemhelper/
├── __main__.py        Entry point: starts TUI + FastAPI thread
├── app.py             Textual Application (screen registry, CSS, keybindings)
├── api_server.py      Wraps web/backend/main.py FastAPI app
├── cec_control.py     HDMI-CEC via cec-client subprocess
├── config/
│   ├── ini_manager.py     Read/write both INI files
│   ├── system_config.py   system-config.ini dataclass
│   └── validator.py       Pre-save validation
├── discovery/
│   ├── scanner.py         Async LAN ping sweep
│   ├── hikvision.py       Hikvision ISAPI probe
│   ├── reolink.py         Reolink HTTP API probe
│   ├── onvif_probe.py     WS-Discovery + ONVIF SOAP
│   └── result.py          CameraDiscoveryResult dataclass
├── screens/
│   ├── dashboard.py       Home: streams, system info, quick actions
│   ├── camera_manager.py  Add/edit/delete cameras + auto-discovery
│   ├── layout_editor.py   Per-screen layout + window assignments
│   ├── network.py         WiFi, hostname, mDNS
│   ├── system.py          Timezone, display, HEVC, audio
│   ├── cec.py             CEC enable/disable, test, bus scan
│   ├── speedtest.py       speedtest-cli runner
│   └── about.py           Version info, Pi hardware
├── widgets/
│   ├── stream_preview.py  Stream status dot widget
│   ├── layout_thumb.py    ASCII-art layout thumbnail
│   ├── camera_row.py      Camera list row widget
│   ├── confirm_dialog.py  Yes/No modal dialog
│   └── spinner.py         Async spinner animation
├── requirements.txt
└── camplayer-systemhelper.service   systemd unit
```
