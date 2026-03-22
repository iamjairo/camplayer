import asyncio
import os
import sys
from configparser import ConfigParser

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Button, Input, Label, Static, ProgressBar
from textual.containers import Horizontal, Vertical
from textual import work

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from discovery.result import CameraDiscoveryResult
from discovery.scanner import scan_subnet


class CameraManagerScreen(Screen):
    """
    Camera management:
    - Left panel:  list of configured cameras (from camplayer-config.ini)
    - Right panel: edit form for selected camera (name, URLs, test button)
    - Bottom:      auto-discovery section (scan LAN, click to add discovered cameras)
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="camera-list-panel", classes="panel"):
                yield Label("Configured Cameras", classes="section-header")
                yield DataTable(id="camera-table")
                with Horizontal():
                    yield Button("+ Add", id="btn-add", variant="success")
                    yield Button("✕ Delete", id="btn-delete", variant="error")
            with Vertical(id="camera-edit-panel", classes="panel"):
                yield Label("Edit Camera", classes="section-header")
                yield Label("Name:")
                yield Input(id="inp-name", placeholder="Front Door")
                yield Label("Main Stream URL:")
                yield Input(id="inp-url-main", placeholder="rtsp://admin:pass@192.168.1.10/stream1")
                yield Label("Sub Stream URL (optional):")
                yield Input(id="inp-url-sub", placeholder="rtsp://admin:pass@192.168.1.10/stream2")
                yield Label("Low Stream URL (optional):")
                yield Input(id="inp-url-low", placeholder="rtsp://admin:pass@192.168.1.10/stream3")
                with Horizontal():
                    yield Button("💾 Save", id="btn-save", variant="primary")
                    yield Button("🔗 Test", id="btn-test", variant="default")
                yield Static(id="test-result")
        with Vertical(id="discovery-panel", classes="panel"):
            yield Label("Auto-Discovery (LAN Scan)", classes="section-header")
            with Horizontal():
                yield Button("🔍 Scan Network", id="btn-scan", variant="primary")
                yield Button("Stop", id="btn-stop-scan", variant="default")
                yield ProgressBar(id="scan-progress", total=254, show_eta=False)
            yield DataTable(id="discovery-table")
            yield Button("+ Add Selected", id="btn-add-discovered", variant="success")

    def on_mount(self) -> None:
        self._selected_device: int | None = None
        self._selected_channel: int | None = None
        self._scan_running = False
        self._discovered: list[CameraDiscoveryResult] = []

        cam_table = self.query_one("#camera-table", DataTable)
        cam_table.add_columns("ID", "Name", "Main URL")
        cam_table.cursor_type = "row"

        disc_table = self.query_one("#discovery-table", DataTable)
        disc_table.add_columns("IP", "Brand", "Model", "Name", "Main Stream")
        disc_table.cursor_type = "row"

        self._load_cameras()

    def _load_cameras(self) -> None:
        """Load cameras from camplayer-config.ini into the table."""
        cam_table = self.query_one("#camera-table", DataTable)
        cam_table.clear()
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            for device in cfg.devices:
                for ch_num, channel in device.channels.items():
                    url = channel.urls[0] if channel.urls else ""
                    url_display = url[:40] + "…" if len(url) > 41 else url
                    cam_table.add_row(
                        f"D{device.id}/CH{ch_num}",
                        channel.name,
                        url_display,
                        key=f"{device.id}:{ch_num}",
                    )
        except Exception as exc:
            self.notify(f"Error loading config: {exc}", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Populate edit form when a row is selected in the camera table."""
        if event.data_table.id != "camera-table":
            return
        try:
            row_key = str(event.row_key.value)
            device_id, ch_num = map(int, row_key.split(":"))
            self._selected_device = device_id
            self._selected_channel = ch_num

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            for device in cfg.devices:
                if device.id == device_id and ch_num in device.channels:
                    channel = device.channels[ch_num]
                    self.query_one("#inp-name", Input).value = channel.name
                    urls = channel.urls
                    self.query_one("#inp-url-main", Input).value = urls[0] if len(urls) > 0 else ""
                    self.query_one("#inp-url-sub", Input).value = urls[1] if len(urls) > 1 else ""
                    self.query_one("#inp-url-low", Input).value = urls[2] if len(urls) > 2 else ""
                    break
        except Exception as exc:
            self.notify(f"Error loading camera: {exc}", severity="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-save":
            self._save_camera()
        elif btn_id == "btn-delete":
            self._delete_camera()
        elif btn_id == "btn-add":
            self._add_new_camera()
        elif btn_id == "btn-test":
            self._test_stream()
        elif btn_id == "btn-scan":
            self._start_scan()
        elif btn_id == "btn-stop-scan":
            self._scan_running = False
        elif btn_id == "btn-add-discovered":
            self._add_discovered_camera()

    def _save_camera(self) -> None:
        """Save the edited camera back to camplayer-config.ini."""
        if self._selected_device is None or self._selected_channel is None:
            self.notify("No camera selected.", severity="warning")
            return
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config, serialize_config
            from models import Channel

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)

            name = self.query_one("#inp-name", Input).value.strip()
            main_url = self.query_one("#inp-url-main", Input).value.strip()
            sub_url = self.query_one("#inp-url-sub", Input).value.strip()
            low_url = self.query_one("#inp-url-low", Input).value.strip()
            urls = [u for u in [main_url, sub_url, low_url] if u]

            for device in cfg.devices:
                if device.id == self._selected_device:
                    device.channels[self._selected_channel] = Channel(name=name, urls=urls)
                    break

            serialize_config(cfg, config_path)
            self._load_cameras()
            self.notify("Camera saved.", severity="information")
        except Exception as exc:
            self.notify(f"Save failed: {exc}", severity="error")

    def _delete_camera(self) -> None:
        if self._selected_device is None or self._selected_channel is None:
            self.notify("No camera selected.", severity="warning")
            return
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config, serialize_config

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            for device in cfg.devices:
                if device.id == self._selected_device:
                    device.channels.pop(self._selected_channel, None)
                    if not device.channels:
                        cfg.devices = [d for d in cfg.devices if d.id != self._selected_device]
                    break

            serialize_config(cfg, config_path)
            self._selected_device = None
            self._selected_channel = None
            self._load_cameras()
            self.notify("Camera deleted.", severity="information")
        except Exception as exc:
            self.notify(f"Delete failed: {exc}", severity="error")

    def _add_new_camera(self) -> None:
        """Add a blank new camera (next available device/channel slot)."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config, serialize_config
            from models import Device, Channel

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            next_id = max((d.id for d in cfg.devices), default=0) + 1
            cfg.devices.append(Device(id=next_id, channels={1: Channel(name="New Camera", urls=[])}))
            serialize_config(cfg, config_path)
            self._load_cameras()
            self.notify(f"Added Device {next_id}.", severity="information")
        except Exception as exc:
            self.notify(f"Add failed: {exc}", severity="error")

    @work(thread=True)
    def _test_stream(self) -> None:
        """Test the main stream URL with a quick ffprobe or TCP connect."""
        url = self.app.call_from_thread(
            lambda: self.query_one("#inp-url-main", Input).value.strip()
        )
        if not url:
            self.app.call_from_thread(
                self.query_one("#test-result", Static).update,
                "No URL to test.",
            )
            return
        try:
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=format_name",
                 "-of", "default=noprint_wrappers=1", url],
                capture_output=True, text=True, timeout=8
            )
            msg = "✓ Stream OK" if result.returncode == 0 else f"✗ Error: {result.stderr[:80]}"
        except FileNotFoundError:
            # ffprobe not available — try TCP connect to host:port
            try:
                import socket
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.hostname or ""
                port = parsed.port or (554 if url.startswith("rtsp") else 80)
                with socket.create_connection((host, port), timeout=3):
                    msg = f"✓ TCP connect to {host}:{port} OK (ffprobe not installed)"
            except Exception as e:
                msg = f"✗ Cannot reach host: {e}"
        except Exception as exc:
            msg = f"✗ {exc}"

        self.app.call_from_thread(
            self.query_one("#test-result", Static).update, msg
        )

    @work(exclusive=True)
    async def _start_scan(self) -> None:
        """Scan the local LAN for cameras."""
        self._scan_running = True
        self._discovered.clear()
        disc_table = self.query_one("#discovery-table", DataTable)
        disc_table.clear()
        progress = self.query_one("#scan-progress", ProgressBar)
        progress.update(progress=0)

        def on_progress(scanned: int, total: int) -> None:
            self.app.call_from_thread(progress.update, progress=scanned)

        try:
            async for result in scan_subnet(progress_cb=on_progress):
                if not self._scan_running:
                    break
                self._discovered.append(result)
                url_display = result.main_stream[:40] + "…" if len(result.main_stream) > 41 else result.main_stream
                disc_table.add_row(
                    result.ip,
                    result.brand,
                    result.model,
                    result.name,
                    url_display,
                    key=result.ip,
                )
        except Exception as exc:
            self.notify(f"Scan error: {exc}", severity="error")
        finally:
            self._scan_running = False
            self.notify(f"Scan complete. Found {len(self._discovered)} camera(s).", severity="information")

    def _add_discovered_camera(self) -> None:
        """Add the selected discovered camera to the config."""
        disc_table = self.query_one("#discovery-table", DataTable)
        if disc_table.cursor_row < 0:
            self.notify("No camera selected from discovery.", severity="warning")
            return
        try:
            row_key = str(disc_table.get_row_at(disc_table.cursor_row)[0])
            result = next((r for r in self._discovered if r.ip == row_key), None)
            if not result:
                return

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "web", "backend"))
            from config_parser import parse_config, serialize_config
            from models import Device, Channel

            config_path = getattr(self.app, "config_path", "/boot/camplayer-config.ini")
            cfg = parse_config(config_path)
            next_id = max((d.id for d in cfg.devices), default=0) + 1
            urls = [u for u in [result.main_stream, result.sub_stream] if u]
            cfg.devices.append(
                Device(id=next_id, channels={1: Channel(name=result.name or f"{result.brand} {result.ip}", urls=urls)})
            )
            serialize_config(cfg, config_path)
            self._load_cameras()
            self.notify(f"Added {result.name or result.ip}.", severity="information")
        except Exception as exc:
            self.notify(f"Add failed: {exc}", severity="error")
