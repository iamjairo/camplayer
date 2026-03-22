import asyncio
import json
import os
import stat
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config_parser import (
    CONFIG_PATH_DEFAULT,
    get_raw_ini,
    parse_config,
    serialize_config,
    set_raw_ini,
)
from go2rtc_sync import GO2RTC_CONFIG_PATH, generate_go2rtc_config, get_stream_id
from models import (
    AdvancedConfig,
    CamplayerConfig,
    Device,
    Layout,
    Screen,
    StreamStatus,
    SystemInfo,
    WindowAssignment,
)

GO2RTC_URL = os.getenv("GO2RTC_URL", "http://localhost:1984")
CONFIG_PATH = os.getenv("CAMPLAYER_CONFIG", CONFIG_PATH_DEFAULT)
RUNTIME_CONFIG_PATH = os.getenv("CAMPLAYER_RUNTIME_CONFIG", "/dev/shm/camplayer-config.ini")
CAMPLAYER_CMD_PIPE = "/dev/shm/camplayer-cmd"


# ── WebSocket connection manager ─────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        text = json.dumps(message)
        dead: list[WebSocket] = []
        for conn in list(self.active_connections):
            try:
                await conn.send_text(text)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.disconnect(conn)


manager = ConnectionManager()


# ── Config file watcher ──────────────────────────────────────────────────────

class _ConfigChangeHandler(FileSystemEventHandler):
    """Watchdog handler that fires an asyncio callback when CONFIG_PATH changes."""

    def __init__(self, loop: asyncio.AbstractEventLoop, callback) -> None:
        super().__init__()
        self._loop = loop
        self._callback = callback

    def on_modified(self, event):
        if not event.is_directory and event.src_path == CONFIG_PATH:
            asyncio.run_coroutine_threadsafe(self._callback(), self._loop)

    def on_created(self, event):
        self.on_modified(event)


async def _on_config_changed() -> None:
    """Regenerate go2rtc config and notify WS clients when the INI changes."""
    try:
        cfg = parse_config(CONFIG_PATH)
        generate_go2rtc_config(cfg, GO2RTC_CONFIG_PATH)
        await manager.broadcast({"event": "config_changed"})
    except Exception as exc:
        await manager.broadcast({"event": "config_error", "detail": str(exc)})


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Regenerate go2rtc config on startup
    try:
        cfg = parse_config(CONFIG_PATH)
        generate_go2rtc_config(cfg, GO2RTC_CONFIG_PATH)
    except Exception:
        pass  # config may not exist yet in fresh installs

    # Start watchdog file watcher in a background thread
    loop = asyncio.get_event_loop()
    handler = _ConfigChangeHandler(loop, _on_config_changed)
    observer = Observer()
    watch_dir = str(Path(CONFIG_PATH).parent)
    observer.schedule(handler, watch_dir, recursive=False)
    observer.start()

    yield

    observer.stop()
    observer.join()


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(title="Camplayer API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_config() -> CamplayerConfig:
    try:
        return parse_config(CONFIG_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Config file not found: {CONFIG_PATH}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse config: {exc}")


def _save_config(cfg: CamplayerConfig) -> None:
    try:
        serialize_config(cfg, CONFIG_PATH)
        generate_go2rtc_config(cfg, GO2RTC_CONFIG_PATH)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write config: {exc}")


def _write_cmd(cmd: str) -> dict:
    """Write a command string to the camplayer IPC named pipe."""
    try:
        pipe = Path(CAMPLAYER_CMD_PIPE)
        if not pipe.exists():
            return {"status": "no_camplayer_process"}
        # Ensure it is actually a FIFO
        if not stat.S_ISFIFO(pipe.stat().st_mode):
            return {"status": "no_camplayer_process"}
        # Open non-blocking; if no reader the OS raises ENXIO
        fd = os.open(CAMPLAYER_CMD_PIPE, os.O_WRONLY | os.O_NONBLOCK)
        try:
            os.write(fd, (cmd + "\n").encode())
        finally:
            os.close(fd)
        return {"status": "ok", "command": cmd}
    except OSError:
        return {"status": "no_camplayer_process"}


# ── Config endpoints ──────────────────────────────────────────────────────────

@app.get("/api/config", response_model=CamplayerConfig)
async def get_config():
    return _load_config()


@app.put("/api/config", response_model=CamplayerConfig)
async def put_config(cfg: CamplayerConfig):
    _save_config(cfg)
    return cfg


@app.get("/api/config/raw", response_class=PlainTextResponse)
async def get_config_raw():
    try:
        return get_raw_ini(CONFIG_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config file not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.put("/api/config/raw")
async def put_config_raw(body: dict):
    ini_text: str = body.get("ini", "")
    if not ini_text:
        raise HTTPException(status_code=400, detail="Missing 'ini' key in request body")
    try:
        set_raw_ini(ini_text, CONFIG_PATH)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid INI: {exc}")
    # Regenerate go2rtc config after raw write
    try:
        cfg = parse_config(CONFIG_PATH)
        generate_go2rtc_config(cfg, GO2RTC_CONFIG_PATH)
    except Exception:
        pass
    return {"status": "ok"}


# ── Device endpoints ──────────────────────────────────────────────────────────

@app.get("/api/devices", response_model=list[Device])
async def get_devices():
    return _load_config().devices


@app.get("/api/devices/{device_id}", response_model=Device)
async def get_device(device_id: int):
    cfg = _load_config()
    for dev in cfg.devices:
        if dev.id == device_id:
            return dev
    raise HTTPException(status_code=404, detail=f"Device {device_id} not found")


@app.put("/api/devices/{device_id}", response_model=Device)
async def put_device(device_id: int, device: Device):
    cfg = _load_config()
    # Ensure the id in the body matches the path
    device = device.model_copy(update={"id": device_id})
    updated = False
    new_devices = []
    for dev in cfg.devices:
        if dev.id == device_id:
            new_devices.append(device)
            updated = True
        else:
            new_devices.append(dev)
    if not updated:
        new_devices.append(device)
        new_devices.sort(key=lambda d: d.id)
    cfg = cfg.model_copy(update={"devices": new_devices})
    _save_config(cfg)
    return device


@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: int):
    cfg = _load_config()
    original_len = len(cfg.devices)
    new_devices = [d for d in cfg.devices if d.id != device_id]
    if len(new_devices) == original_len:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    cfg = cfg.model_copy(update={"devices": new_devices})
    _save_config(cfg)
    return {"status": "ok", "deleted": device_id}


# ── Screen endpoints ──────────────────────────────────────────────────────────

@app.get("/api/screens", response_model=list[Screen])
async def get_screens():
    return _load_config().screens


@app.get("/api/screens/{screen_id}", response_model=Screen)
async def get_screen(screen_id: int):
    cfg = _load_config()
    for scr in cfg.screens:
        if scr.id == screen_id:
            return scr
    raise HTTPException(status_code=404, detail=f"Screen {screen_id} not found")


@app.put("/api/screens/{screen_id}", response_model=Screen)
async def put_screen(screen_id: int, screen: Screen):
    cfg = _load_config()
    screen = screen.model_copy(update={"id": screen_id})
    updated = False
    new_screens = []
    for scr in cfg.screens:
        if scr.id == screen_id:
            new_screens.append(screen)
            updated = True
        else:
            new_screens.append(scr)
    if not updated:
        new_screens.append(screen)
        new_screens.sort(key=lambda s: s.id)
    cfg = cfg.model_copy(update={"screens": new_screens})
    _save_config(cfg)
    return screen


# ── Streams (go2rtc proxy) ────────────────────────────────────────────────────

@app.get("/api/streams", response_model=list[StreamStatus])
async def get_streams():
    """Return all configured streams enriched with live go2rtc status."""
    cfg = _load_config()

    # Build a map of stream_id → url from the config
    stream_urls: dict[str, str] = {}
    for device in cfg.devices:
        for ch_num in sorted(device.channels):
            channel = device.channels[ch_num]
            for idx, url in enumerate(channel.urls):
                sid = get_stream_id(device.id, ch_num, idx)
                stream_urls[sid] = url

    # Query go2rtc for live status
    live_data: dict = {}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{GO2RTC_URL}/api/streams", timeout=3.0)
            if resp.status_code == 200:
                live_data = resp.json() or {}
    except Exception:
        pass

    results: list[StreamStatus] = []
    for sid, url in stream_urls.items():
        live = live_data.get(sid, {})
        producers = live.get("producers") or []
        consumers = live.get("consumers") or []
        tracks: list[str] = []
        for p in producers:
            tracks.extend(p.get("tracks") or [])
        results.append(StreamStatus(
            stream_id=sid,
            url=url,
            active=bool(producers),
            consumers=len(consumers),
            tracks=tracks,
        ))

    return results


@app.post("/api/streams/{stream_id}/probe")
async def probe_stream(stream_id: str):
    """Ask go2rtc to probe a stream and return available track info."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GO2RTC_URL}/api/streams",
                params={"src": stream_id},
                timeout=10.0,
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"go2rtc returned {resp.status_code}",
                )
            data = resp.json() or {}
            stream = data.get(stream_id, {})
            producers = stream.get("producers") or []
            tracks: list[str] = []
            for p in producers:
                tracks.extend(p.get("tracks") or [])
            return {"stream_id": stream_id, "tracks": tracks, "raw": stream}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"go2rtc probe failed: {exc}")


# ── Layout control ────────────────────────────────────────────────────────────

@app.get("/api/layout")
async def get_layout():
    """Return active layout info from runtime config if available."""
    runtime_path = RUNTIME_CONFIG_PATH
    try:
        from config_parser import parse_config as _parse
        active_cfg = _parse(runtime_path)
        return {
            "source": "runtime",
            "screens": [
                {
                    "id": s.id,
                    "display": s.display,
                    "layout": int(s.layout),
                    "layout_name": s.layout.name,
                    "window_count": len(s.windows),
                }
                for s in active_cfg.screens
            ],
        }
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # Fall back to the static config
    try:
        cfg = _load_config()
        return {
            "source": "static",
            "screens": [
                {
                    "id": s.id,
                    "display": s.display,
                    "layout": int(s.layout),
                    "layout_name": s.layout.name,
                    "window_count": len(s.windows),
                }
                for s in cfg.screens
            ],
        }
    except HTTPException:
        raise


@app.post("/api/layout/next")
async def layout_next():
    """Advance to the next screen."""
    return _write_cmd("next")


@app.post("/api/layout/prev")
async def layout_prev():
    """Go back to the previous screen."""
    return _write_cmd("prev")


@app.post("/api/layout/screen/{screen_num}")
async def layout_go_to_screen(screen_num: int):
    """Jump directly to a specific screen number (1-based)."""
    return _write_cmd(f"screen:{screen_num}")


# ── Health + system ───────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    go2rtc_ok = False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GO2RTC_URL}/api/streams", timeout=2.0)
            go2rtc_ok = r.status_code == 200
    except Exception:
        pass
    return {"status": "ok", "go2rtc": go2rtc_ok}


@app.get("/api/system", response_model=SystemInfo)
async def get_system():
    """Read system information from Pi hardware and environment."""
    # Pi model
    pi_model = "Unknown"
    try:
        pi_model = Path("/proc/device-tree/model").read_text().rstrip("\x00").strip()
    except Exception:
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("Model"):
                    pi_model = line.split(":", 1)[1].strip()
                    break
        except Exception:
            pass

    # Hardware decoder capability (from /proc/cpuinfo Hardware field)
    hwdec = "none"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("Hardware"):
                hw = line.split(":", 1)[1].strip()
                # BCM2711 = Pi 4, BCM2712 = Pi 5
                if "BCM2712" in hw:
                    hwdec = "rpi5"
                elif "BCM2711" in hw:
                    hwdec = "rpi4"
                elif "BCM" in hw:
                    hwdec = "rpi"
                else:
                    hwdec = hw.lower()
                break
    except Exception:
        pass

    # GPU memory (vcgencmd)
    gpu_memory_mb = 0
    try:
        result = subprocess.run(
            ["vcgencmd", "get_mem", "gpu"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            # output: "gpu=128M\n"
            match = result.stdout.strip()
            num = match.replace("gpu=", "").replace("M", "")
            gpu_memory_mb = int(num)
    except Exception:
        pass

    # OS version
    os_version = "Unknown"
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                os_version = line.split("=", 1)[1].strip().strip('"')
                break
    except Exception:
        pass

    # Camplayer version
    camplayer_version = "unknown"
    for candidate in [
        Path("/app/VERSION"),
        Path("/config/VERSION"),
        Path(__file__).parent.parent.parent / "VERSION",
    ]:
        try:
            camplayer_version = candidate.read_text().strip()
            break
        except Exception:
            continue

    # go2rtc version
    go2rtc_version: Optional[str] = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{GO2RTC_URL}/api", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                go2rtc_version = data.get("version") or data.get("go2rtc_version")
    except Exception:
        pass

    return SystemInfo(
        pi_model=pi_model,
        hwdec=hwdec,
        gpu_memory_mb=gpu_memory_mb,
        os_version=os_version,
        camplayer_version=camplayer_version,
        go2rtc_version=go2rtc_version,
    )


# ── WebSocket: stream status events ──────────────────────────────────────────

@app.websocket("/ws/status")
async def ws_status(websocket: WebSocket):
    """Broadcast config-change and stream-status events to connected clients."""
    await manager.connect(websocket)
    try:
        while True:
            # Keepalive: echo any received text back as a pong
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
